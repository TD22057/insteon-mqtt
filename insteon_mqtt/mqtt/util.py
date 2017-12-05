#===========================================================================
#
# MQTT utilities
#
#===========================================================================


def clean_topic(topic):
    """Clean up input topics

    This removes any trailing '/' characters and strips whitespace
    from the ends.

    Arg:
       topic:  (str) The input topic.

    Returns:
       (str) Returns the cleaned topic.
    """
    topic = topic.strip()
    if topic.endswith("/"):
        return topic[:-1].strip()

    return topic.strip()

#===========================================================================
