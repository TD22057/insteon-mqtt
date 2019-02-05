#===========================================================================
#
# select.poll based network manager.
#
#===========================================================================
import errno
import select
import time
from .. import log

LOG = log.get_logger(__name__)


class Manager:
    """Poll based network event loop manager.

    This class implements a networking event loop (poll or select) using the
    select.poll system (so it's not supported on Windows).

    Network connections (or files, sockets, etc) should inherit from the Link
    class which will manage the communication with this class and handle
    reading and writing callbacks.

    If a link reports that it is not connected yet (or it drops the
    connection later), the manager will poll the link at Manager.min_time_out
    to try and reconnect it if Link.retry_connect_dt() is active.

    Create the manager, then the links, then call poll() to start the loop.

        mgr = Manager()
        mgr.add( MyLink(...) )
        mgr.add( MyLink(...) )
        while mgr.active():
            mgr.select(time_out=1)
            # do something that requires polling here.
    """
    # Minimum time out - used to poll links for reconnection and other random
    # processing.
    min_time_out = 3  # seconds

    # Bit flags to watch for when registering a socket for read or
    # read/write.
    READ = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
    READ_WRITE = READ | select.POLLOUT

    # Bit flags reported for events.
    EVENT_READ = select.POLLIN | select.POLLPRI
    EVENT_WRITE = select.POLLOUT
    EVENT_CLOSE = select.POLLHUP
    EVENT_ERROR = select.POLLERR

    #-----------------------------------------------------------------------
    def __init__(self):
        """Constructor.
        """
        self.poll = select.poll()

        # Map of fileno to Link objects.
        self.links = {}

        # List of unconnected link tuples (Link, time) where time is the time
        # is the next time to try reconnecting the linnk.
        self.unconnected = []

        # Time out to use when trying to reconnect links.
        self.unconnected_time_out = 1.0  # sec

    #-----------------------------------------------------------------------
    def active(self):
        """Returns non-zero if the link has active links or unconnected links.
        """
        return len(self.links) + len(self.unconnected)

    #-----------------------------------------------------------------------
    def add(self, link, connected=True):
        """Add a Link to the manager.

        To remove a link, call link.close().

        Args:
          link (Link):  Link object to add to the manager.
          connected (bool):  True if the link is already connected.  False
                    if the manager should try and connect the link itself.
        """
        LOG.debug("Link added: %s", link)

        # If the link is connected, we can get it's file descriptor and add
        # it to the polling loop.
        if connected:
            fd = link.fileno()
            self.poll.register(fd, self.READ)

            # Connect the link signals so we know when it closes or needs to
            # write data.
            link.signal_closing.connect(self.link_closing)
            link.signal_needs_write.connect(self.link_needs_write)

            self.links[fd] = link

            # Now that the fd is registered, we can notify others that the
            # links is ready to read or write.
            link.signal_connected.emit(link, True)

        # For unconnected links, store them for later checking.
        else:
            data = (link, time.time())
            self.unconnected.append(data)

    #-----------------------------------------------------------------------
    def remove(self, link):
        """Remove a link from the manager.

        To remove a link, call link.close() - this method should generally
        not be used to remove the link.

        Args:
          link (Link):  The link to remove.  If the link isn't in the
               manager, nothing is done.
        """
        fd = link.fileno()
        if fd not in self.links:
            return

        link.signal_closing.disconnect(self.link_closing)
        link.signal_needs_write.disconnect(self.link_needs_write)

        self.poll.unregister(fd)
        self.links.pop(fd, None)

        LOG.debug("Link removed %s", link)

    #-----------------------------------------------------------------------
    def close_all(self):
        """Close all the links in the manager.

        This wlil call Link.close() to shut the links down.
        """
        # We can't iterate over the links dict because call close will remove
        # items from that dict when the callbacks happen.  So copy the value
        # and iterate over that.
        links = list(self.links.values())
        for l in links:
            l.close()

    #-----------------------------------------------------------------------
    def select(self, time_out=None):
        """Run one iteration of the event loop.

        This will run one select.poll() call to wait for any of the link file
        descriptors to have data to read or write.  When a Link activates for
        reading or writing, the various methods on the link will be called to
        handle the action.

        Arg:
           time_out (int):  Time out to use in seconds.  The actual time out
                    value is is the minimum of this, the manager reconnect
                    time out and the unconnected retry time out.
        """
        # Get the actual time out to use.
        time_out = Manager.min_time_out if time_out is None else time_out
        if self.unconnected:
            time_out = min(time_out, self.unconnected_time_out)

        time_out *= 1000  # sec->msec

        # Keep polling until we get a successfull call with events.
        while True:
            try:
                # events = (fileno, bit flags) of the actions.
                events = self.poll.poll(time_out)
            except OSError as err:
                # This error can occur sometimes when using a timeout.  It
                # should be ignored and the poll retried.
                if err.errno != errno.EINTR:
                    raise
            else:
                # No error was thrown so break out of the while loop.
                break

        # Handle any links that need to be connected.
        t = time.time()
        for i in range(len(self.unconnected) - 1, -1, -1):
            link, next_time = self.unconnected[i]

            # If we're after the reconnect time, try and connect the linkn.
            if t >= next_time:
                LOG.debug("Link connection attempt %s", link)
                if link.connect():
                    # Connection success - add the link to the manager.
                    LOG.debug("Link connection success %s", link)
                    self.add(link)
                    del self.unconnected[i]
                else:
                    LOG.debug("Link connection failed %s", link)
                    self.unconnected[i] = (link, t + link.retry_connect_dt())

        for fd, flag in events:
            # Map the fileno to the Link object.
            link = self.links.get(fd, None)
            if link is None:
                continue

            # Link has data to read.  If reading has an error, clear the
            # action flag so nothing else happens.
            if flag & self.EVENT_READ:
                if link.read_from_link() == -1:
                    flag = 0

            # Link has data to write.
            if flag & self.EVENT_WRITE:
                link.write_to_link(t)

            # File/socket is shutting down - close the link.
            if flag & self.EVENT_CLOSE:
                link.close()

            # Unknown error occurred - this is fatal so close the link.
            elif flag & self.EVENT_ERROR:
                link.close()

        # Poll the links in case they need to do brute force processing of
        # any kind.  There are some cases where the MQTT client poll can
        # trigger a close - I'm not sure exactly why but it's shown up in
        # user reports.  So copy the links before iterating since closing the
        # link mods the dict which isn't allowed.
        for link in list(self.links.values()):
            link.poll(t)

    #-----------------------------------------------------------------------
    def link_closing(self, link):
        """Callback when a link is closing.

        This is called when the Link.close() occurs.  It will remove the link
        from the manager.  If the link.return_connect_dt() returns a time,
        the link is added to the unconnected list for later re-connection.

        Arg:
          link (Link):  The link that is closing.
        """
        self.remove(link)

        dt = link.retry_connect_dt()
        if dt and dt > 0:
            data = (link, time.time() + dt)
            self.unconnected.append(data)

        # Emit the connected signal to let anyone else know that the link is
        # no longer connected.
        link.signal_connected.emit(link, False)

    #-----------------------------------------------------------------------
    def link_needs_write(self, link, needs_write):
        """Callback when a link write status changes state.

        This is called when the link write status changes state.  When the
        link has data to write, we need to add it to the write notification
        list and then remove it when all the data has been written.  This
        callback manages that state and is called when the
        link.signal_needs_write is emitted.

        Arg:
          link (Link):  The link changing state.
          needs_write (bool):  True if the link has data to write.  False
                      if the link no longer has data to write.
        """
        if needs_write:
            self.poll.modify(link.fileno(), self.READ_WRITE)
        else:
            self.poll.modify(link.fileno(), self.READ)

    #-----------------------------------------------------------------------
