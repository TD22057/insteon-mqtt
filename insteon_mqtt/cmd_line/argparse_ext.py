#===========================================================================
#
# Extend Argparse to Enable Sub-Parser Groups
#
# Based on this very old issue: https://bugs.python.org/issue9341
#
# Adds the method `add_parser_group()` to the sub-parser class.
# This adds a group heading to the sub-parser list, just like the
# `add_argument_group()` method.
#
# NOTE: As noted on the issue page, this probably won't work with [parents].
# see http://bugs.python.org/issue16807
#
#===========================================================================
# Pylint doesn't like us access protected items like this
#pylint:disable=protected-access,abstract-method
import argparse


class _SubParsersAction(argparse._SubParsersAction):

    class _PseudoGroup(argparse.Action):

        def __init__(self, container, title):
            sup = super(_SubParsersAction._PseudoGroup, self)
            sup.__init__(option_strings=[], dest=title)
            self.container = container
            self._choices_actions = []

        def add_parser(self, name, **kwargs):
            # add the parser to the main Action, but move the pseudo action
            # in the group's own list
            parser = self.container.add_parser(name, **kwargs)
            choice_action = self.container._choices_actions.pop()
            self._choices_actions.append(choice_action)
            return parser

        def _get_subactions(self):
            return self._choices_actions

        def add_parser_group(self, title):
            # the formatter can handle recursive subgroups
            grp = _SubParsersAction._PseudoGroup(self, title)
            self._choices_actions.append(grp)
            return grp

    def add_parser_group(self, title):
        #
        grp = _SubParsersAction._PseudoGroup(self, title)
        self._choices_actions.append(grp)
        return grp


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register('action', 'parsers', _SubParsersAction)
