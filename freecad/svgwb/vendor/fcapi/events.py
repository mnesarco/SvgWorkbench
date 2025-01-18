# SPDX-License: LGPL-3.0-or-later
# (c) 2024 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from PySide.QtCore import (  # type: ignore[attr-defined]
    QObject,
    QTimer,
    Signal,
    Qt,
)

import FreeCAD as App  # type: ignore[all]

from dataclasses import dataclass
from contextlib import suppress
from typing import Any, Protocol, TypeVar, TYPE_CHECKING
import functools
import inspect
import weakref

from .utils import ref_is_valid

if TYPE_CHECKING:
    import FreeCADGui as Gui  # type: ignore
    from pivy import coin  # type: ignore

# Event timer
# ===========
# Tick for custom state events
_event_timer = QTimer()
_event_timer.setInterval(10)
_event_timer.start()


class EventListener(Protocol):
    """(event) -> None"""

    def __call__(self, event: Any) -> None: ...


class EventListenerMethod(Protocol):
    """(self, event) -> None"""

    def __call__(self, owner: Any, event: Any) -> None: ...


class EventSubscription:
    """
    Subscription to an EventSource. Allows to unsubscribe.

    Example:
    ========
    unsubscribe = source.subscribe(fn)
    ...
    unsubscribe()
    """

    __slots__ = ("source", "listener", "_method_id", "__weakref__")

    def __init__(self, listener: EventListener, source: BaseEventSource):
        try:
            self.listener = weakref.WeakMethod(listener)
            self._method_id = hash(listener.__name__)
        except TypeError:
            self.listener = weakref.ref(listener)
            self._method_id = id(listener)
        self.source = weakref.ref(source)

    def __call__(self) -> None:
        if (listener := self.listener()) is not None and (source := self.source()) is not None:
            try:
                source.trigger.disconnect(listener)
            except Exception:
                pass  # Already disconnected, ok

    def _id(self):
        return self._method_id, id(self.source)

    # Alias
    unsubscribe = __call__


class EventSubscriptions:
    """
    Manage event subscriptions without duplicates.
    """

    def __init__(self):
        self._data = {}

    def __iadd__(self, subscription):
        if (_id := subscription._id()) in self._data:
            # if attempt to duplicate a subscription
            # the existing one is kept and
            # the new one is unsubscribed
            self._unsubscribe(subscription)
        else:
            self._data[_id] = subscription
        return self

    def _unsubscribe(self, subs):
        try:
            subs.detach()
        except NameError:
            subs.unsubscribe()

    def unsubscribe(self):
        for subs in self._data.values():
            self._unsubscribe(subs)
        self._data = {}


class EventSubscriptionsDescriptor:
    def __get__(self, owner, obj_type=None):
        if subscriptions := getattr(owner, self.attr_name, None):
            return subscriptions

        subscriptions = EventSubscriptions()
        setattr(owner, self.attr_name, subscriptions)
        return subscriptions

    def __set_name__(self, cls: type, name: str):
        self.attr_name = f"_{cls.__name__}_fcapi_subs_{name}"


class BaseEventSource(QObject):
    """
    Basic Event source, it is a callable that emit events.
    """

    trigger = Signal(object)

    def __init__(self, parent: QObject | None = None):
        QObject.__init__(self, parent)

    def __call__(self, event) -> None:
        self.trigger.emit(event)

    def subscribe(self, listener: EventListener, connection=Qt.AutoConnection) -> EventSubscription:
        self.trigger.connect(listener, connection)
        return EventSubscription(listener, self)


class StateEventState(dict[str, Any]):
    """
    State of custom state events.
    """

    disabled: bool

    def __init__(self):
        super().__init__()
        self.disabled = False

    def disable(self):
        self.disabled = True

    def enable(self):
        self.disabled = False


EventType = TypeVar("EventType")


class StateEventProducer(Protocol[EventType]):
    """(state: StateEventState) -> EventType | None"""

    def __call__(self, state: StateEventState) -> EventType | None: ...


class StateEventSource(BaseEventSource):
    """
    Custom event source with state.
    """

    state: StateEventState

    def __init__(self):
        super().__init__(_event_timer)
        self.state = StateEventState()


def state_event(*, one_shot: bool = False):
    def deco(producer: StateEventProducer):
        """Decorator to create custom state event producers."""
        source = StateEventSource()

        def timeout():
            if source.state.disabled:
                _event_timer.timeout.disconnect(timeout)
                return
            if event := producer(source.state):
                source(event)

        _event_timer.timeout.connect(timeout)
        return EventDef(source, one_shot)

    return deco


class MethodEventListenerDescriptor:
    """
    Special descriptor to defer signal connection of methods until instance creation.

    Used in conjunction with decorators to turn method definitions into instances
    of this descriptor. At the end of the class definition the __init__ method
    is injected with code that connect the instance bound methods to the
    corresponding event sources.

    Inheritance note:
        subclasses must call super().__init__(...) to setup parent listeners.
    """

    def __init__(self, method: EventListenerMethod, source: BaseEventSource, one_shot: bool = False):
        self.method = method
        self.source = source
        self.one_shot = one_shot

    def __get__(self, owner, obj_type=None):
        bound_method = self.method.__get__(owner, obj_type)
        if self.one_shot:
            def one_shot_listener(event):
                try:
                    self.source.trigger.disconnect(one_shot_listener)
                except Exception:
                    pass # Already disconnected, ok
                bound_method(event)
            return one_shot_listener
        return bound_method

    def __set_name__(self, cls: type, method_name: str):
        """
        Collect all descriptors and wrap __init__.

        Key facts:
        1. This method is called at the end of class definition, once per descriptor.
        2. All descriptors are collected in cls._{cls.__name__}_fcapi_listeners.
        3. key mangling is required to manage inheritance properly.
        4. __init__ is wrapped once if there is at least one descriptor.
        """
        key = f"_{cls.__name__}_fcapi_listeners"
        if listeners := getattr(cls, key, None):
            listeners[method_name] = self
        else:
            setattr(cls, key, {method_name: self})
            self.setup(cls, key)

    def setup(self, cls, key: str):
        """
        Wrap cls.__init__ to inject code to connect all sources to instance methods.
        """
        obj_init = cls.__init__

        def init_wrapper(self_, *args, **kwargs):
            listeners: dict[str, MethodEventListenerDescriptor] = getattr(self_, key)
            for name, desc in listeners.items():
                desc.source.subscribe(getattr(self_, name))
            obj_init(self_, *args, **kwargs)

        functools.update_wrapper(init_wrapper, obj_init)
        cls.__init__ = init_wrapper


class EventDef:
    """
    Event manager definition.

    This callable can be used as decorator to subscribe to the event (typical usage)
    and emit method is used to send events to all subscribers.
    """

    source: BaseEventSource

    def __init__(self, source: BaseEventSource | None = None, one_shot: bool = False):
        self.source = source or BaseEventSource()
        self.one_shot = one_shot

    def __call__(self, listener: EventListenerMethod | EventListener):
        arity = len(inspect.signature(listener).parameters)
        if arity == 2:  # Method
            return MethodEventListenerDescriptor(listener, self.source, self.one_shot)
        if arity == 1:  # Free function
            if self.one_shot:

                def _listener(event):
                    listener.unsubscribe()
                    listener(event)

            else:
                _listener = listener
            listener.unsubscribe = self.source.subscribe(_listener)
            return listener
        raise TypeError("Listener must accept a single argument: event")

    # Alias
    subscribe = __call__

    def emit(self, event):
        self.source(event)


@dataclass(slots=True)
class SelectionItemResult:
    doc: App.Document | None
    obj: App.DocumentObject | None = None
    sub: str | None = None
    pnt: tuple | None = None


class events:
    """Namespace of builtin events."""

    @dataclass(slots=True)
    class DocumentEvent:
        doc: App.Document

    @dataclass(slots=True)
    class DocumentPropertyEvent:
        doc: App.Document
        prop: str

    @dataclass(slots=True)
    class DocumentSaveEvent:
        doc: App.Document
        path: str

    @dataclass(slots=True)
    class TransactionEvent:
        doc: App.Document
        name: str | None = None

    @dataclass(slots=True)
    class DocumentObjectEvent:
        obj: App.DocumentObject

    @dataclass(slots=True)
    class DocumentObjectPropertyEvent:
        obj: App.DocumentObject
        prop: str

    @dataclass(slots=True)
    class DocumentObjectExtensionEvent:
        obj: App.DocumentObject
        extension: str

    # --- Selection

    @dataclass(slots=True, frozen=True)
    class SelectionEvent:
        doc: str | None = None
        obj: str | None = None
        sub: str | None = None
        pnt: tuple | None = None

        def fetch(self) -> SelectionItemResult:
            doc = App.getDocument(self.doc)
            obj = doc.getObject(self.obj) if doc and self.obj else None
            return SelectionItemResult(doc, obj, self.sub, self.pnt)

    # --- App

    @dataclass(slots=True)
    class GuiUpEvent:
        pass

    class document:
        """Namespace of Document events"""

        created = EventDef()
        deleted = EventDef()
        relabeled = EventDef()
        activated = EventDef()
        recomputed = EventDef()
        before_recompute = EventDef()
        undo = EventDef()
        redo = EventDef()
        before_change = EventDef()
        changed = EventDef()
        before_save = EventDef()
        saved = EventDef()

    class transaction:
        """Namespace of transaction events"""

        open = EventDef()
        commit = EventDef()
        abort = EventDef()
        before_close = EventDef()
        closed = EventDef()

    class doc_object:
        """Namespace of document object events"""

        created = EventDef()
        deleted = EventDef()
        before_recompute = EventDef()
        recomputed = EventDef()
        before_change = EventDef()
        changed = EventDef()
        property_added = EventDef()
        property_removed = EventDef()
        property_editor_changed = EventDef()
        extension_added = EventDef()
        before_adding_extension = EventDef()

    class selection:
        added = EventDef()
        removed = EventDef()
        clear = EventDef()
        set = EventDef()
        set_pre = EventDef()
        removed_pre = EventDef()
        picked_list_changed = EventDef()

    class app:
        @state_event(one_shot=True)
        def gui_up(state: StateEventState):
            if App.GuiUp:
                return events.GuiUpEvent()


# [FreeCAD API] SelectionObserver
class _DocumentObserver:
    """
    Private Internal DocumentObserver implementation.
    """

    def slotCreatedDocument(self, doc: App.Document):
        events.document.created.emit(events.DocumentEvent(doc))

    def slotDeletedDocument(self, doc: App.Document):
        events.document.deleted.emit(events.DocumentEvent(doc))

    def slotRelabelDocument(self, doc: App.Document):
        events.document.relabeled.emit(events.DocumentEvent(doc))

    def slotActivateDocument(self, doc: App.Document):
        events.document.activated.emit(events.DocumentEvent(doc))

    def slotRecomputedDocument(self, doc: App.Document):
        events.document.recomputed.emit(events.DocumentEvent(doc))

    def slotBeforeRecomputeDocument(self, doc: App.Document):
        events.document.before_recompute.emit(events.DocumentEvent(doc))

    def slotUndoDocument(self, doc: App.Document):
        events.document.undo.emit(events.DocumentEvent(doc))

    def slotRedoDocument(self, doc: App.Document):
        events.document.redo.emit(events.DocumentEvent(doc))

    def slotChangedDocument(self, doc: App.Document, prop: str):
        events.document.changed.emit(events.DocumentPropertyEvent(doc, prop))

    def slotBeforeChangeDocument(self, doc: App.Document, prop: str):
        events.document.before_change.emit(events.DocumentPropertyEvent(doc, prop))

    def slotStartSaveDocument(self, doc: App.Document, path: str):
        events.document.before_save.emit(events.DocumentSaveEvent(doc, path))

    def slotFinishSaveDocument(self, doc: App.Document, path: str):
        events.document.saved.emit(events.DocumentSaveEvent(doc, path))

    # --- Transaction

    def slotOpenTransaction(self, doc: App.Document, name: str):
        events.transaction.open.emit(events.TransactionEvent(doc, name))

    def slotCommitTransaction(self, doc: App.Document):
        events.transaction.commit.emit(events.TransactionEvent(doc))

    def slotAbortTransaction(self, doc: App.Document):
        events.transaction.abort.emit(events.TransactionEvent(doc))

    def slotBeforeCloseTransaction(self, doc: App.Document):
        events.transaction.before_close.emit(events.TransactionEvent(doc))

    def slotCloseTransaction(self, doc: App.Document):
        events.transaction.closed.emit(events.TransactionEvent(doc))

    # --- DocumentObject

    def slotCreatedObject(self, obj: App.DocumentObject):
        events.doc_object.created.emit(events.DocumentObjectEvent(obj))

    def slotDeletedObject(self, obj: App.DocumentObject):
        events.doc_object.deleted.emit(events.DocumentObjectEvent(obj))

    def slotChangedObject(self, obj: App.DocumentObject, prop: str):
        events.doc_object.changed.emit(events.DocumentObjectPropertyEvent(obj, prop))

    def slotBeforeChangeObject(self, obj: App.DocumentObject, prop: str):
        events.doc_object.before_change.emit(events.DocumentObjectPropertyEvent(obj, prop))

    def slotRecomputedObject(self, obj: App.DocumentObject):
        events.doc_object.recomputed.emit(events.DocumentObjectEvent(obj))

    def slotAppendDynamicProperty(self, obj: App.DocumentObject, prop: str):
        events.doc_object.property_added.emit(events.DocumentObjectPropertyEvent(obj, prop))

    def slotRemoveDynamicProperty(self, obj: App.DocumentObject, prop: str):
        events.doc_object.property_removed.emit(events.DocumentObjectPropertyEvent(obj, prop))

    def slotChangePropertyEditor(self, obj: App.DocumentObject, prop: str):
        events.doc_object.property_editor_changed.emit(
            events.DocumentObjectPropertyEvent(obj, prop)
        )

    def slotBeforeAddingDynamicExtension(self, obj: App.DocumentObject, extension: str):
        events.doc_object.before_adding_extension.emit(
            events.DocumentObjectExtensionEvent(obj, extension)
        )

    def slotAddedDynamicExtension(self, obj: App.DocumentObject, extension: str):
        events.doc_object.extension_added.emit(events.DocumentObjectExtensionEvent(obj, extension))


# [FreeCAD API] SelectionObserver
class _SelectionObserver:
    """
    Private Internal SelectionObserver implementation.
    """

    def setPreselection(self, doc: str, obj: str, sub: str):
        events.selection.set_pre.emit(events.SelectionEvent(doc, obj, sub))

    def addSelection(self, doc: str, obj: str, sub: str, pnt: App.Vector):
        events.selection.added.emit(events.SelectionEvent(doc, obj, sub, pnt))

    def removeSelection(self, doc: str, obj: str, sub: str):
        events.selection.removed.emit(events.SelectionEvent(doc, obj, sub))

    def setSelection(self, doc: str):
        events.selection.set.emit(events.SelectionEvent(doc))

    def clearSelection(self, doc: str):
        events.selection.clear.emit(events.SelectionEvent(doc))

    def pickedListChanged(self):
        events.selection.picked_list_changed.emit(events.SelectionEvent())

    def removePreselection(self, doc: str, obj: str, sub: str):
        events.selection.removed_pre.emit(events.SelectionEvent(doc, obj, sub))


class ViewCallback:
    """
    Callback attachable to view events for: DraggerCallback, EventCallback, EventCallbackPivy
    """

    __slots__ = ("event", "callback", "view", "dragger", "_method_id", "__weakref__")

    def __init__(self, event: str | coin.SoType, callback: callable, method_id: int):
        self.event = event
        self.callback = callback
        self.view: Gui.View3DInventorPy | None = None
        self.dragger = None
        self._method_id = method_id

    def _attach_dragger(self, view: Gui.View3DInventorPy, dragger=None):
        view.addDraggerCallback(dragger, self.event, self.callback)
        self.dragger = dragger

    def attach(self, view: Gui.View3DInventorPy, *, dragger=None):
        if self.view:
            self.detach()

        if isinstance(self.event, str):
            if dragger:
                self._attach_dragger(view, dragger)
            else:
                view.addEventCallback(self.event, self.callback)
        else:
            view.addEventCallbackPivy(self.event, self.callback)
        self.view = view
        return self

    def detach(self, view: Gui.View3DInventorPy | None = None, dragger=None):
        if dragger and not view:
            msg = "If dragger is passed, view must be passed too."
            raise ValueError(msg)

        if view and not dragger and self.dragger:
            msg = "dragger is missing"
            raise ValueError(msg)

        # View objects can be deleted from c++, in that case
        # detaching will fail but it is ok to ignore it.
        with suppress(Exception):
            if target := (view or self.view):
                if not ref_is_valid(target):
                    return
                if isinstance(self.event, str):
                    if t_dragger := (dragger or self.dragger):
                        target.removeDraggerCallback(t_dragger, self.event, self.callback)
                    else:
                        target.removeEventCallback(self.event, self.callback)
                else:
                    target.removeEventCallbackPivy(self.event, self.callback)
                if not view:
                    self.view = None
                    self.dragger = None

    def __call__(self, *args, **kwargs):
        self.callback(*args, **kwargs)

    def _id(self):
        return self._method_id, id(self.view), id(self.dragger), self.event


class ViewCallbackDescriptor:
    def __init__(self, method: callable, event: str | coin.SoType):
        self.method = method
        self.event = event

    def __get__(self, owner, obj_type=None):
        bound_method = self.method.__get__(owner, obj_type)
        return ViewCallback(self.event, bound_method, id(self.method))


class view_callback:
    """Decorator to configure a method as a view event callback."""

    def __init__(self, event: str | coin.SoType):
        self.event = event

    def __call__(self, callback: callable):
        return ViewCallbackDescriptor(callback, self.event)


# Install the DocumentObserver Singleton
App.addDocumentObserver(_DocumentObserver())


# Lazy install of Selection Observer Singleton
@events.app.gui_up
def on_gui(event):
    App.Gui.Selection.addObserver(
        _SelectionObserver(),
        App.Gui.Selection.ResolveMode.NewStyleElement,
    )
