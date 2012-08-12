#------------------------------------------------------------------------------
#  Copyright (c) 2012, Enthought, Inc.
#  All rights reserved.
#------------------------------------------------------------------------------
from traits.api import Enum, Bool, Property, cached_property

from .constraints_widget import ConstraintsWidget
from .page import Page


class Notebook(ConstraintsWidget):
    """ A component which displays its children as tabbed pages.
    
    A Notebook is similar to a TabControl, but has more features. It is
    typically used in document style editing situations where the user
    should have rich control over the layout of their documents.

    """
    #: The position of tabs in the notebook.
    tab_position = Enum('top', 'bottom', 'left', 'right')

    #: Whether or not the tabs in the notebook should be closable.
    tabs_closable = Bool(True)

    #: Whether or not the tabs in the notebook should be movable.
    tabs_movable = Bool(True)

    #: Whether or not the tabs in the notebook should be dockable.
    tabs_dockable = Bool(True)

    #: A read only property which returns the notebook's Pages.
    pages = Property(depends_on='children[]')

    #: How strongly a component hugs it's contents' width. A Notebook
    #: ignores its width hug by default, so it expands freely in width.
    hug_width = 'ignore'

    #: How strongly a component hugs it's contents' height. A Notebook
    #: ignores its height hug by default, so it expands freely in height.
    hug_height = 'ignore'

    #--------------------------------------------------------------------------
    # Initialization
    #--------------------------------------------------------------------------
    def snapshot(self):
        """ Returns the snapshot for the control.

        """
        snap = super(Notebook, self).snapshot()
        snap['page_ids'] = self._snap_page_ids()
        snap['tab_position'] = self.tab_position
        snap['tabs_closable'] = self.tabs_closable
        snap['tabs_movable'] = self.tabs_movable
        snap['tabs_dockable'] = self.tabs_dockable
        return snap

    def bind(self):
        """ Bind the change handlers for the control.

        """
        super(Notebook, self).bind()
        attrs = (
            'tab_position', 'tabs_closable', 'tabs_movable', 'tabs_dockable'
        )
        self.publish_attributes(*attrs)

    #--------------------------------------------------------------------------
    # Private API
    #--------------------------------------------------------------------------
    @cached_property
    def _get_pages(self):
        """ The getter for the 'pages' property.

        Returns
        -------
        result : tuple
            The tuple of Page instances defined as children of this
            Notebook.

        """
        isinst = isinstance
        pages = (child for child in self.children if isinst(child, Page))
        return tuple(pages)

    def _snap_page_ids(self):
        """ Returns the widget ids of the notebook's pages.

        """
        return [page.widget_id for page in self.pages]

