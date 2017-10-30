#===========================================================================
#
# Network and serial link management
#
#===========================================================================
import errno
import logging
import select
import time


class Manager:
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
        self.poll = select.poll()
        self.links = {}
        self.unconnected = []
        self.unconnected_time_out = 0.100  # sec

        self.log = logging.getLogger(__name__)

    #-----------------------------------------------------------------------
    def active(self):
        return len(self.links)

    #-----------------------------------------------------------------------
    def add(self, link, connected=True):
        self.log.debug("Link added", link)

        if connected:
            fd = link.fileno()
            self.poll.register(fd, self.READ)

            link.signal_closing.connect(self.link_closing)
            link.signal_needs_write.connect(self.link_needs_write)

            self.links[fd] = link
        else:
            data = (link, time.time())
            self.unconnected.append(data)

    #-----------------------------------------------------------------------
    def remove(self, link):
        fd = link.fileno()

        link.signal_closing.disconnect(self.link_closing)
        link.signal_needs_write.disconnect(self.link_needs_write)

        self.poll.unregister(fd)
        self.links.pop(fd, None)

        self.log.debug("Link removed", link)

    #-----------------------------------------------------------------------
    def close_all(self):
        links = self.links.values()
        for l in links:
            l.close()

    #-----------------------------------------------------------------------
    def select(self, time_out=None):
        time_out = None if time_out is None else 1000*time_out
        if self.unconnected and not time_out:
            time_out = 1000*self.unconnected_time_out

        while True:
            try:
                events = self.poll.poll(time_out)
            except select.error as e:
                if e[0] != errno.EINTR:
                    raise
            else:
                break

        t = time.time()
        for i in range(len(self.unconnected)-1, -1, -1):
            link, next_time = self.unconnected[i]
            if t >= next_time:
                self.log.debug("Link connection attempt", link)
                if link.connect():
                    self.log.debug("Link connection success", link)
                    self.add(link)
                    del self.unconnected[i]
                else:
                    self.log.debug("Link connection failed", link)
                    self.unconnected[i] = (link, t+link.retry_connect_dt())

        for fd, flag in events:
            #print("   found fd=%s" % fd )
            link = self.links.get(fd, None)
            if link is None:
                continue

            if flag & self.EVENT_READ:
                #print("   link read")
                if link.read_from_link() == -1:
                    flag = 0

            if flag & self.EVENT_WRITE:
                #print("   link write")
                link.write_to_link()

            if flag & self.EVENT_CLOSE:
                #print("   link close")
                link.close()

            elif flag & self.EVENT_ERROR:
                #print("   link error")
                link.close()

    #-----------------------------------------------------------------------
    def link_closing(self, link):
        self.remove(link)

        dt = link.retry_connect_dt()
        if dt and dt > 0:
            data = (link, time.time() + dt)
            self.unconnected.append(data)

    #-----------------------------------------------------------------------
    def link_needs_write(self, link, needs_write):
        if needs_write:
            self.poll.modify(link.fileno(), self.READ_WRITE)
        else:
            self.poll.modify(link.fileno(), self.READ)

    #-----------------------------------------------------------------------
