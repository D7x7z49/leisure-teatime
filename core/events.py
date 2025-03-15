# core/events.py
from abc import ABC, abstractmethod
from functools import wraps
from typing import Callable, Dict, List, Tuple, Any, Type, Literal, Union
import inspect
import asyncio
import threading

from core.logging import get_logger

logger = get_logger("events")

class EventHandler(ABC):
    """Base class for defining event handlers for class methods."""

    @classmethod
    @abstractmethod
    def get_scope(cls) -> Tuple[Type, List[str]]:
        """Return the scope (class type) and method names this handler applies to."""
        pass

    @classmethod
    @abstractmethod
    def before(cls, target: Any, *args, **kwargs) -> None:
        """Handler to execute before the target method, for input validation or logging."""
        pass

    @classmethod
    @abstractmethod
    def after(cls, target: Any, result: Any, *args, **kwargs) -> None:
        """Handler to execute after the target method, for result logging or statistics."""
        pass

    @classmethod
    def add(cls, timing: Literal['before', 'after'] = 'before', priority: int = 10) -> None:
        """Register this handler for the specified method(s)."""
        scope, method_names = cls.get_scope()
        handler = cls.before if timing == 'before' else cls.after
        EventRegistry.register_event(method_names, scope, handler, timing, priority)
        logger.message("Finished").subject("method").details(
            timing=timing, scope=scope.__qualname__, methods=method_names
        ).log("debug")

    @classmethod
    def remove(cls, timing: Literal['before', 'after'] = 'before') -> None:
        """Remove this handler from the specified method(s)."""
        scope, method_names = cls.get_scope()
        handler = cls.before if timing == 'before' else cls.after
        EventRegistry.remove_event(method_names, scope, handler, timing)
        logger.message("Finished").subject("method").details(
            timing=timing, scope=scope.__qualname__, methods=method_names
        ).log("debug")

class EventRegistry:
    """Registry for event handlers, scoped to class methods, with thread safety and async support."""

    _lock = threading.Lock()  # Thread safety lock
    _handlers: Dict[str, Dict[str, List[Tuple[int, Literal['before', 'after'], Callable]]]] = {}
    _injected: Dict[str, Dict[str, bool]] = {}  # Track injected methods to avoid duplicate wrapping
    enable_events = True  # Global switch to enable/disable event handling

    @classmethod
    def _get_scope_key(cls, scope: Type, method_name: str) -> str:
        """Generate a unique key for the scope (class and method)."""
        return f"{scope.__qualname__}.{method_name}"

    @classmethod
    def event_handler(cls, scope: Type, timing: Literal['before', 'after'] = 'before', priority: int = 10):
        """Decorator to register an event handler for a class method."""
        def decorator(handler: Callable) -> Callable:
            handler_sig = inspect.signature(handler)
            if len(handler_sig.parameters) < 1:
                raise ValueError("Event handler must accept at least one parameter (target)")
            if timing == 'after' and len(handler_sig.parameters) < 2:
                raise ValueError("After event handler must accept at least two parameters (target, result)")

            def register_method(method_name: Union[str, List[str]]):
                cls.register_event(method_name, scope, handler, timing, priority)
                logger.message("Finished").subject("method").details(
                    timing=timing, scope=scope.__qualname__, method=method_name
                ).log("debug")
                return handler

            return register_method
        return decorator

    @classmethod
    def register_event(cls, method_name: Union[str, List[str]], scope: Type, handler: Callable, timing: Literal['before', 'after'] = 'before', priority: int = 10):
        """Dynamically register an event handler for class method(s) and inject event handling logic."""
        if not cls.enable_events:
            return

        with cls._lock:
            method_names = [method_name] if isinstance(method_name, str) else method_name
            handler_sig = inspect.signature(handler)
            if len(handler_sig.parameters) < 1:
                raise ValueError("Event handler must accept at least one parameter (target)")
            if timing == 'after' and len(handler_sig.parameters) < 2:
                raise ValueError("After event handler must accept at least two parameters (target, result)")

            for m_name in method_names:
                scope_key = cls._get_scope_key(scope, m_name)
                if scope_key not in cls._handlers:
                    cls._handlers[scope_key] = {}
                if m_name not in cls._handlers[scope_key]:
                    cls._handlers[scope_key][m_name] = []
                cls._handlers[scope_key][m_name].append((priority, timing, handler))
                cls._handlers[scope_key][m_name].sort(key=lambda x: x[0])

                if scope_key not in cls._injected or not cls._injected[scope_key].get(m_name):
                    if not hasattr(scope, m_name):
                        raise ValueError(f"Method '{m_name}' does not exist in {scope.__qualname__}")
                    original_method = getattr(scope, m_name)
                    is_async = inspect.iscoroutinefunction(original_method)

                    if is_async:
                        @wraps(original_method)
                        async def async_wrapper(self_or_cls, *args, **kwargs):
                            handlers = cls._handlers.get(scope_key, {}).get(m_name, [])
                            for _, t, h in handlers:
                                if t == 'before':
                                    try:
                                        if inspect.iscoroutinefunction(h):
                                            await h(self_or_cls, *args, **kwargs)
                                        else:
                                            h(self_or_cls, *args, **kwargs)
                                    except Exception as e:
                                        logger.message("Error").subject("chain").details(
                                            msg=f"Before handler failed for {scope.__qualname__}.{m_name}", exc=str(e)
                                        ).log("error")
                            result = await original_method(self_or_cls, *args, **kwargs)
                            for _, t, h in handlers:
                                if t == 'after':
                                    try:
                                        if inspect.iscoroutinefunction(h):
                                            await h(self_or_cls, result, *args, **kwargs)
                                        else:
                                            h(self_or_cls, result, *args, **kwargs)
                                    except Exception as e:
                                        logger.message("Error").subject("chain").details(
                                            msg=f"After handler failed for {scope.__qualname__}.{m_name}", exc=str(e)
                                        ).log("error")
                            return result
                        wrapper = async_wrapper
                    else:
                        @wraps(original_method)
                        def sync_wrapper(self_or_cls, *args, **kwargs):
                            handlers = cls._handlers.get(scope_key, {}).get(m_name, [])
                            for _, t, h in handlers:
                                if t == 'before':
                                    try:
                                        h(self_or_cls, *args, **kwargs)
                                    except Exception as e:
                                        logger.message("Error").subject("chain").details(
                                            msg=f"Before handler failed for {scope.__qualname__}.{m_name}", exc=str(e)
                                        ).log("error")
                            result = original_method(self_or_cls, *args, **kwargs)
                            for _, t, h in handlers:
                                if t == 'after':
                                    try:
                                        h(self_or_cls, result, *args, **kwargs)
                                    except Exception as e:
                                        logger.message("Error").subject("chain").details(
                                            msg=f"After handler failed for {scope.__qualname__}.{m_name}", exc=str(e)
                                        ).log("error")
                            return result
                        wrapper = sync_wrapper

                    setattr(scope, m_name, wrapper)
                    if scope_key not in cls._injected:
                        cls._injected[scope_key] = {}
                    cls._injected[scope_key][m_name] = True

    @classmethod
    def remove_event(cls, method_name: Union[str, List[str]], scope: Type, handler: Callable, timing: Literal['before', 'after'] = 'before'):
        """Remove an event handler from the specified method(s)."""
        if not cls.enable_events:
            return

        with cls._lock:
            method_names = [method_name] if isinstance(method_name, str) else method_name
            for m_name in method_names:
                scope_key = cls._get_scope_key(scope, m_name)
                if scope_key in cls._handlers and m_name in cls._handlers[scope_key]:
                    cls._handlers[scope_key][m_name] = [(p, t, h) for p, t, h in cls._handlers[scope_key][m_name] if not (t == timing and h == handler)]
                    if not cls._handlers[scope_key][m_name]:
                        del cls._handlers[scope_key][m_name]
                        if not cls._handlers[scope_key]:
                            del cls._handlers[scope_key]

def __main__():
    class MyClass:
        async def foo(self, x):
            return x * 2

    class MyHandler(EventHandler):
        @classmethod
        def get_scope(cls):
            return MyClass, ["foo"]

        @classmethod
        async def before(cls, target, x):
            print(f"Before foo: x={x}")

        @classmethod
        async def after(cls, target, result, x):
            print(f"After foo: result={result}")

    MyHandler.add("before")
    MyHandler.add("after")

    obj = MyClass()
    asyncio.run(obj.foo(3))

if __name__ == "__main__":
    __main__()
