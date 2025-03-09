# core/utils/data.py
import inspect
from typing import Union, Iterator, Optional
from functools import reduce, wraps
from collections import deque
from playwright.sync_api import Page as SyncPage
from playwright.async_api import Page as AsyncPage
from lxml import etree
from core.logging import get_logger

logger = get_logger("data.utils")

def _parse_html_content(content: Union[str, Iterator[str]]) -> Optional[etree.Element]:
    """Parse HTML content into lxml Element."""
    try:
        if isinstance(content, str):
            tree = etree.HTML(content)
        elif hasattr(content, "__iter__"):
            tree = etree.HTML("".join(content))
        else:
            raise ValueError("Input must be str or iterable")
        return tree if tree is not None else None
    except Exception as e:
        logger.error(f"Failed to parse HTML content: {e}")
        return None

def extract_lxml(source: Union[SyncPage, str, Iterator[str]], xpath: str = "//body") -> Optional[etree.Element]:
    """Extract lxml Element using XPath from sync source."""
    try:
        if isinstance(source, SyncPage):
            content = source.content()
        else:
            content = source

        tree = _parse_html_content(content)
        if tree is None:
            return None

        nodes = tree.xpath(xpath)
        return nodes[0] if nodes else tree
    except Exception as e:
        logger.error(f"Failed to extract lxml from sync source: {e}")
        return None

async def async_extract_lxml(source: Union[AsyncPage, str, Iterator[str]], xpath: str = "//body") -> Optional[etree.Element]:
    """Extract lxml Element using XPath from async source."""
    try:
        if isinstance(source, AsyncPage):
            content = await source.content()
        else:
            content = source

        tree = _parse_html_content(content)
        if tree is None:
            return None

        nodes = tree.xpath(xpath)
        return nodes[0] if nodes else tree
    except Exception as e:
        logger.error(f"Failed to extract lxml from async source: {e}")
        return None

class DataProcessor:
    _event_handlers = {}

    @classmethod
    def register_event(cls, methods=None, before=None, after=None, priority=0):
        """注册方法的事件处理器"""
        if methods is None:
            methods = ['process', 'get', 'fork', 'get_stage', 'rollback', 'step', 'build']

        for method_name in methods:
            if method_name not in cls._event_handlers:
                cls._event_handlers[method_name] = {'before': [], 'after': []}
            if before:
                cls._event_handlers[method_name]['before'].append((priority, before))
                cls._event_handlers[method_name]['before'].sort(key=lambda x: x[0], reverse=True)
            if after:
                cls._event_handlers[method_name]['after'].append((priority, after))
                cls._event_handlers[method_name]['after'].sort(key=lambda x: x[0], reverse=True)

    def event_handler(method):
        """修饰器：包装实例方法，执行事件处理器"""
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            method_name = method.__name__

            # 调用前处理
            if method_name in self._event_handlers:
                for _, before_handler in self._event_handlers[method_name]['before']:
                    before_handler(self, *args, **kwargs)

            # 执行方法
            result = method(self, *args, **kwargs)

            # 调用后处理
            if method_name in self._event_handlers:
                for _, after_handler in self._event_handlers[method_name]['after']:
                    after_handler(self, result, *args, **kwargs)

            return result
        return wrapper

    def __init__(self, initial_state, upstream=None, upstream_stages=0):
        self.initial_state = initial_state
        self.upstream = upstream
        self.upstream_stages = upstream_stages
        self.callbacks = deque()
        self.head = 0

    @event_handler
    def process(self, callback):
        self.callbacks.append(callback)
        self.head += 1
        return self

    @event_handler
    def get(self):
        state = self.initial_state
        for i in range(self.head):
            try:
                state = self.callbacks[i](state)
            except Exception as e:
                raise ValueError(f"第 {i + 1} 个回调函数执行失败: {e}")
        return state

    @event_handler
    def fork(self):
        new_instance = DataProcessor(
            initial_state=self.get(),
            upstream=self,
            upstream_stages=self.get_stage()
        )
        return new_instance

    @event_handler
    def get_stage(self):
        return self.upstream_stages + self.head

    @event_handler
    def rollback(self, steps=1):
        target_stage = self.get_stage() - steps
        if target_stage < 0:
            raise ValueError("回退超过主链路起点")

        current = self
        while current.upstream is not None:
            if current.upstream.get_stage() <= target_stage:
                target_head = target_stage - current.upstream.upstream_stages
                current = current.upstream
                break
            current = current.upstream
        else:
            target_head = target_stage

        current.head = target_head
        new_instance = current.fork()
        current.step()
        return new_instance

    @event_handler
    def step(self):
        self.head = len(self.callbacks)
        return self

    @event_handler
    def build(self):
        def compose(f, g):
            return lambda x: f(g(x))

        all_callbacks = deque()
        current = self
        while current is not None:
            for i in range(current.head):
                all_callbacks.appendleft(current.callbacks[i])
            current = current.upstream

        if not all_callbacks:
            return lambda x: x
        return reduce(compose, all_callbacks)



# 示例使用
if __name__ == "__main__":

    # 示例事件处理器
    def print_get_result(processor, result, *args, **kwargs):
        """get 方法调用后打印结果"""
        print(f"Get result: {result}")

    def check_process_callback(processor, callback=None, *args, **kwargs):
        """process 方法调用前检查回调类型"""
        if callback is not None:  # 仅当 callback 存在时检查
            if not callable(callback):
                raise TypeError(f"Callback must be callable, got {type(callback)}")
            if not inspect.isfunction(callback) and not inspect.ismethod(callback):
                print(f"Warning: {callback} is callable but not a standard function/method")

    def log_method_call(processor, *args, **kwargs):
        """记录方法调用"""
        print(f"Calling {processor.__class__.__name__} method with args: {args}, kwargs: {kwargs}")

    # 注册事件
    DataProcessor.register_event(methods=["get"], after=print_get_result, priority=1)
    DataProcessor.register_event(methods=["process", "get"], before=check_process_callback, priority=2)
    DataProcessor.register_event(methods=["process"], before=log_method_call, priority=0)

    # 创建主链路
    main = DataProcessor(initial_state=(1, 2))
    main.process(lambda x: (x[0] + 1 if x[0] is not None else 0, x[1]))  # 输出 "Calling ...", 检查类型
    main.process(lambda x: (x[0], x[1] * 2))  # 输出 "Calling ...", 检查类型
    print("Main initial:")
    main.get()  # 输出 "Get result: (2, 4)", 检查类型（callback=None 时跳过）

    # 创建分支
    branch = main.fork()  # 无事件触发
    branch.process(lambda x: (x[0] * 10, x[1]))  # 输出 "Calling ...", 检查类型
    print("Branch:")
    branch.get()  # 输出 "Get result: (20, 4)", 检查类型（callback=None 时跳过）

    # 检查阶段数
    print("Main stage:", main.get_stage())  # 无事件触发
    print("Branch stage:", branch.get_stage())  # 无事件触发

    # 回退操作
    rollback = main.rollback(1)  # 无事件触发
    print("Rollback:")
    rollback.get()  # 输出 "Get result: (2, 2)", 检查类型（callback=None 时跳过）
    print("Main after rollback:")
    main.get()  # 输出 "Get result: (2, 4)", 检查类型（callback=None 时跳过）

    # 测试类型检查
    try:
        main.process("not a function")  # 输出 "Calling ...", 抛出 TypeError
    except TypeError as e:
        print(e)

    # 构建并应用组合函数
    clean_func = main.build()  # 无事件触发
    data = [(1, 2), (None, 3), (1000, 4)]
    cleaned_data = [clean_func(x) for x in data]
    print("Cleaned data:", cleaned_data)  # 输出 [(2, 4), (0, 6), (1000, 8)]
