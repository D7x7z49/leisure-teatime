# core/utils/functional.py
import asyncio
from typing import Callable, Any, TypeVar, Coroutine

T = TypeVar("T")

class AsyncCurried:
    """A curried function that returns an awaitable when fully applied."""
    def __init__(self, fn: Callable[..., Coroutine], *args, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.arg_count = fn.__code__.co_argcount

    def __call__(self, *args) -> Any:
        new_args = self.args + args
        if len(new_args) >= self.arg_count:
            return self.fn(*new_args, **self.kwargs)  # 返回协程对象，需 await
        return AsyncCurried(self.fn, *new_args, **self.kwargs)

def curry(fn: Callable[..., Coroutine]) -> Callable:
    """Curry an async function, returning a sync callable."""
    return AsyncCurried(fn)

async def pipeline(initial: T, steps: list[Callable[[T], Any]]) -> Any:
    """Run a sequence of steps, supporting both sync and async functions."""
    result = initial
    for step in steps:
        if asyncio.iscoroutine(result):
            result = await result
        if asyncio.iscoroutinefunction(step):
            result = await step(result)
        else:
            result = step(result)
    if asyncio.iscoroutine(result):
        result = await result
    return result

async def compose(*funcs: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose functions in reverse order."""
    async def fn(x: Any) -> Any:
        result = x
        for f in reversed(funcs):
            if asyncio.iscoroutinefunction(f):
                result = await f(result)
            else:
                result = f(result)
        return result
    return fn

def asyncify(fn: Callable[..., Any]) -> Callable[..., Coroutine]:
    """Convert a sync function to async."""
    async def wrapper(*args, **kwargs) -> Any:
        return fn(*args, **kwargs)
    return wrapper

# 示例用法
if __name__ == "__main__":
    async def add(a: int, b: int) -> int:
        await asyncio.sleep(1)  # 模拟异步操作
        return a + b

    curried_add = curry(add)
    step1 = curried_add(2)  # 同步返回 AsyncCurried 对象
    result = step1(3)       # 返回协程对象
    print(asyncio.run(pipeline(None, [lambda _: result])))  # 输出: 5
