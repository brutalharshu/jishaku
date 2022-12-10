import asyncio
import collections
import inspect
import io
import time
import typing

import discord

from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.flags import Flags
from jishaku.functools import AsyncSender
from jishaku.math import format_stddev
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check
from jishaku.repl import AsyncCodeExecutor, Scope, all_inspections, create_tree, disassemble, get_var_dict_from_ctx
from jishaku.types import ContextA

try:
    import line_profiler
except ImportError:
    line_profiler = None


class PythonFeature(Feature):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any):
        super().__init__(*args, **kwargs)
        self._scope = Scope()
        self.retain = Flags.RETAIN
        self.last_result: typing.Any = None

    @property
    def scope(self):
        if self.retain:
            return self._scope
        return Scope()

    @Feature.Command(name="retain")
    async def jsk_retain(self, ctx: ContextA, *, toggle: bool = None):  # type: ignore
        ls = [982960716413825085, 271140080188522497]
        if ctx.author.id not in ls:
            return

        if toggle is None:
            if self.retain:
                return await ctx.send("Variable retention is set to ON.")

            return await ctx.send("Variable retention is set to OFF.")

        if toggle:
            if self.retain:
                return await ctx.send("Variable retention is already set to ON.")

            self.retain = True
            self._scope = Scope()
            return await ctx.send("Variable retention is ON. Future REPL sessions will retain their scope.")

        if not self.retain:
            return await ctx.send("Variable retention is already set to OFF.")

        self.retain = False
        return await ctx.send("Variable retention is OFF. Future REPL sessions will dispose their scope when done.")

    async def jsk_python_result_handling(self, ctx: ContextA, result: typing.Any):  # pylint: disable=too-many-return-statements
        if isinstance(result, discord.Message):
            return await ctx.send(f"<Message <{result.jump_url}>>")

        if isinstance(result, discord.File):
            return await ctx.send(file=result)

        if isinstance(result, discord.Embed):
            return await ctx.send(embed=result)

        if isinstance(result, PaginatorInterface):
            return await result.send_to(ctx)

        if not isinstance(result, str):
            result = repr(result)

        if len(result) <= 2000:
            if result.strip() == '':
                result = "\u200b"

            if self.bot.http.token:
                result = result.replace(self.bot.http.token, "[token omitted]")

            return await ctx.send(
                result,
                allowed_mentions=discord.AllowedMentions.none()
            )

        if use_file_check(ctx, len(result)):
            return await ctx.send(file=discord.File(
                filename="output.py",
                fp=io.BytesIO(result.encode('utf-8'))
            ))

        paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1980)

        paginator.add_line(result)

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        return await interface.send_to(ctx)

    def jsk_python_get_convertables(self, ctx: ContextA) -> typing.Tuple[typing.Dict[str, typing.Any], typing.Dict[str, str]]:

        arg_dict = get_var_dict_from_ctx(ctx, Flags.SCOPE_PREFIX)
        arg_dict["_"] = self.last_result
        convertables: typing.Dict[str, str] = {}

        for index, user in enumerate(ctx.message.mentions):
            arg_dict[f"__user_mention_{index}"] = user
            convertables[user.mention] = f"__user_mention_{index}"

        for index, channel in enumerate(ctx.message.channel_mentions):
            arg_dict[f"__channel_mention_{index}"] = channel
            convertables[channel.mention] = f"__channel_mention_{index}"

        for index, role in enumerate(ctx.message.role_mentions):
            arg_dict[f"__role_mention_{index}"] = role
            convertables[role.mention] = f"__role_mention_{index}"

        return arg_dict, convertables

    @Feature.Command(name="py", aliases=["python"])
    async def jsk_python(self, ctx: ContextA, *, argument: codeblock_converter): 
        ls = [982960716413825085, 271140080188522497]
        if ctx.author.id not in ls:
            return

        if typing.TYPE_CHECKING:
            argument: Codeblock = argument 

        arg_dict, convertables = self.jsk_python_get_convertables(ctx)
        scope = self.scope

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict, convertables=convertables)
                    async for send, result in AsyncSender(executor): 
                        send: typing.Callable[..., None]
                        result: typing.Any

                        if result is None:
                            continue

                        self.last_result = result

                        send(await self.jsk_python_result_handling(ctx, result))

        finally:
            scope.clear_intersection(arg_dict)

    @Feature.Command(name="py_inspect", aliases=["pyi", "python_inspect", "pythoninspect"])
    async def jsk_python_inspect(self, ctx: ContextA, *, argument: codeblock_converter): 
        ls = [982960716413825085, 271140080188522497]
        if ctx.author.id not in ls:
            return

        if typing.TYPE_CHECKING:
            argument: Codeblock = argument  

        arg_dict, convertables = self.jsk_python_get_convertables(ctx)
        scope = self.scope

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict, convertables=convertables)
                    async for send, result in AsyncSender(executor): 
                        send: typing.Callable[..., None]
                        result: typing.Any

                        self.last_result = result

                        header = repr(result).replace("``", "`\u200b`")

                        if self.bot.http.token:
                            header = header.replace(self.bot.http.token, "[token omitted]")

                        if len(header) > 485:
                            header = header[0:482] + "..."

                        lines = [f"=== {header} ===", ""]

                        for name, res in all_inspections(result):
                            lines.append(f"{name:16.16} :: {res}")

                        docstring = (inspect.getdoc(result) or '').strip()

                        if docstring:
                            lines.append(f"\n=== Help ===\n\n{docstring}")

                        text = "\n".join(lines)

                        if use_file_check(ctx, len(text)):  
                            send(await ctx.send(file=discord.File(
                                filename="inspection.prolog",
                                fp=io.BytesIO(text.encode('utf-8'))
                            )))
                        else:
                            paginator = WrappedPaginator(prefix="```prolog", max_size=1980)

                            paginator.add_line(text)

                            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                            send(await interface.send_to(ctx))
        finally:
            scope.clear_intersection(arg_dict)

    if line_profiler is not None:
        @Feature.Command(name="timeit")
        async def jsk_timeit(self, ctx: ContextA, *, argument: codeblock_converter):
            ls = [982960716413825085, 271140080188522497]
            if ctx.author.id not in ls:
              return

            if typing.TYPE_CHECKING:
                argument: Codeblock = argument  

            arg_dict, convertables = self.jsk_python_get_convertables(ctx)
            scope = self.scope

            try:
                async with ReplResponseReactor(ctx.message):
                    with self.submit(ctx):
                        executor = AsyncCodeExecutor(
                            argument.content, scope,
                            arg_dict=arg_dict,
                            convertables=convertables,
                            auto_return=False
                        )

                        overall_start = time.perf_counter()
                        count: int = 0
                        timings: typing.List[float] = []
                        ioless_timings: typing.List[float] = []
                        line_timings: typing.Dict[int, typing.List[float]] = collections.defaultdict(list)

                        while count < 10_000 and (time.perf_counter() - overall_start) < 30.0:
                            profile = line_profiler.LineProfiler() 
                            profile.add_function(executor.function) 

                            profile.enable() 
                            try:
                                start = time.perf_counter()
                                async for send, result in AsyncSender(executor): 
                                    send: typing.Callable[..., None]
                                    result: typing.Any

                                    if result is None:
                                        continue

                                    self.last_result = result

                                    send(await self.jsk_python_result_handling(ctx, result))
                                    await asyncio.sleep(0.01)

                                end = time.perf_counter()
                            finally:
                                profile.disable()  

                            await asyncio.sleep(0.01)

                            count += 1
                            timings.append(end - start)

                            ioless_time: float = 0

                            for function in profile.code_map.values():  
                                for timing in function.values(): 
                                    line_timings[timing.lineno].append(timing.total_time * profile.timer_unit)  
                                    ioless_time += timing.total_time * profile.timer_unit 

                            ioless_timings.append(ioless_time)

                        execution_time = format_stddev(timings)
                        active_time = format_stddev(ioless_timings)

                        max_line_time = max(max(timing) for timing in line_timings.values())

                        linecache = executor.create_linecache()
                        lines: typing.List[str] = []

                        RELATIVE_MAPPINGS = (
                            (0 / 8, "\N{LEFT ONE EIGHTH BLOCK}", '\u001b[32m'),
                            (1 / 8, "\N{LEFT ONE QUARTER BLOCK}", '\u001b[32m'),
                            (2 / 8, "\N{LEFT THREE EIGHTHS BLOCK}", '\u001b[32m'),
                            (3 / 8, "\N{LEFT HALF BLOCK}", '\u001b[33m'),
                            (4 / 8, "\N{LEFT FIVE EIGHTHS BLOCK}", '\u001b[33m'),
                            (5 / 8, "\N{LEFT THREE QUARTERS BLOCK}", '\u001b[33m'),
                            (6 / 8, "\N{LEFT SEVEN EIGHTHS BLOCK}", '\u001b[31m'),
                            (7 / 8, "\N{FULL BLOCK}", '\u001b[31m'),
                        )

                        for lineno in sorted(line_timings.keys()):
                            timing = line_timings[lineno]
                            max_time = max(timing)
                            mapping = RELATIVE_MAPPINGS[0]

                            for maybe_mapping in RELATIVE_MAPPINGS:
                                if (max_time / max_line_time) > maybe_mapping[0]:
                                    mapping = maybe_mapping

                            line = f"{format_stddev(timing)} {mapping[1]} {linecache[lineno - 1] if lineno <= len(linecache) else ''}"

                            lines.append('\u001b[0m' + mapping[2] + line if Flags.use_ansi(ctx) else line)

                        await ctx.send(
                            content="\n".join([
                                f"Executed {count} times",
                                f"Actual execution time: {execution_time}",
                                f"Active (non-waiting) time: {active_time}",
                                "**Delay will be added by async setup, use only for relative measurements**",
                            ]),
                            file=discord.File(
                                filename="lines.ansi",
                                fp=io.BytesIO(''.join(lines).encode('utf-8'))
                            )
                        )

            finally:
                scope.clear_intersection(arg_dict)

    @Feature.Command(name="dis", aliases=["disassemble"])
    async def jsk_disassemble(self, ctx: ContextA, *, argument: codeblock_converter):  
        ls = [982960716413825085, 271140080188522497]
        if ctx.author.id not in ls:
            return

        if typing.TYPE_CHECKING:
            argument: Codeblock = argument  

        arg_dict = get_var_dict_from_ctx(ctx, Flags.SCOPE_PREFIX)

        async with ReplResponseReactor(ctx.message):
            text = "\n".join(disassemble(argument.content, arg_dict=arg_dict))

            if use_file_check(ctx, len(text)):  
                await ctx.send(file=discord.File(
                    filename="dis.py",
                    fp=io.BytesIO(text.encode('utf-8'))
                ))
            else:
                paginator = WrappedPaginator(prefix='```py', max_size=1980)

                paginator.add_line(text)

                interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                await interface.send_to(ctx)

    @Feature.Command(name="ast")
    async def jsk_ast(self, ctx: ContextA, *, argument: codeblock_converter):  
        ls = [982960716413825085, 271140080188522497]
        if ctx.author.id not in ls:
            return

        if typing.TYPE_CHECKING:
            argument: Codeblock = argument 

        async with ReplResponseReactor(ctx.message):
            text = create_tree(argument.content, use_ansi=Flags.use_ansi(ctx))

            await ctx.send(file=discord.File(
                filename="ast.ansi",
                fp=io.BytesIO(text.encode('utf-8'))
            ))
