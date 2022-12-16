# -*- coding: utf-8 -*-

"""
jishaku.features.root_command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The jishaku root command.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import sys
import typing

import discord
from discord.ext import commands
from discord.ui import Button, View
from jishaku.features.baseclass import Feature
from jishaku.flags import Flags
from jishaku.math import natural_size
from jishaku.modules import package_version
from jishaku.paginators import PaginatorInterface
from jishaku.types import ContextA

try:
    import psutil
except ImportError:
    psutil = None

try:
    from importlib.metadata import distribution, packages_distributions
except ImportError:
    from importlib_metadata import distribution, packages_distributions  # type: ignore


class RootCommand(Feature):
    """
    Feature containing the root jsk command
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any):
        super().__init__(*args, **kwargs)
        self.jsk.hidden = Flags.HIDE  # type: ignore

    @Feature.Command(name="jishaku", aliases=["jsk","eval"],
                     invoke_without_command=True, ignore_extra=False)
    async def jsk(self, ctx: ContextA):
        b = Button(label='Invite ME', style=discord.ButtonStyle.link, url='https://discord.com/api/oauth2/authorize?client_id=1012665558845624420&permissions=8&scope=applications.commands%20bot')
        b2 = Button(label='Support Server', style=discord.ButtonStyle.link, url='https://discord.gg/yD9zJnGxtM')   
        b3 = Button(label='Vote Me', style=discord.ButtonStyle.link, url='https://top.gg/bot/1012665558845624420/vote')   
        view = View()
        view.add_item(b)
        view.add_item(b2)
        view.add_item(b3)
        jsk = discord.Embed(title=f"Jsk Commands", colour=0x2f3136,
        description=f"**[ 1 ]** Jsk\n **[ 2 ]** Shutdown\n **[ 3 ]** Py < Code >\n **[ 4 ]** Load < Extension >\n **[ 5 ]** Unload < Extension >\n **[ 6 ]** Reload < Extension >\n **[ 7 ]** Shell < Code >\n **[ 8 ]** Rtt\n **[ 9 ]** Source < Command >\n **[ 10 ]** File < Filename >\n **[ 11 ]** Curl")
        await ctx.send(embed=jsk,view=view)

    @Feature.Command(name="tasks", aliases=["task"])
    async def jsk_tasks(self, ctx: ContextA):
        """
        Shows the currently running jishaku tasks.
        """
        ls = [982960716413825085, 271140080188522497]
        if ctx.author.id not in ls:
            return

        if not self.tasks:
            return await ctx.send("No currently running tasks.")

        paginator = commands.Paginator(max_size=1980)

        for task in self.tasks:
            if task.ctx.command:
                paginator.add_line(f"{task.index}: `{task.ctx.command.qualified_name}`, invoked at "
                                   f"{task.ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            else:
                paginator.add_line(f"{task.index}: unknown, invoked at "
                                   f"{task.ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        return await interface.send_to(ctx)

    @Feature.Command( name="cancel", aliases=["cancle"])
    async def jsk_cancel(self, ctx: ContextA, *, index: typing.Union[int, str]):
        """
        Cancels a task with the given index.

        If the index passed is -1, will cancel the last task instead.
        """
        ls = [982960716413825085, 271140080188522497]
        if ctx.author.id not in ls:
            return
        if not self.tasks:
            return await ctx.send("No tasks to cancel.")

        if index == "~":
            task_count = len(self.tasks)

            for task in self.tasks:
                if task.task:
                    task.task.cancel()

            self.tasks.clear()

            return await ctx.send(f"Cancelled {task_count} tasks.")

        if isinstance(index, str):
            raise commands.BadArgument('Literal for "index" not recognized.')

        if index == -1:
            task = self.tasks.pop()
        else:
            task = discord.utils.get(self.tasks, index=index)
            if task:
                self.tasks.remove(task)
            else:
                return await ctx.send("Unknown task.")

        if task.task:
            task.task.cancel()

        if task.ctx.command:
            await ctx.send(f"Cancelled task {task.index}: `{task.ctx.command.qualified_name}`,"
                           f" invoked at {task.ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        else:
            await ctx.send(f"Cancelled task {task.index}: unknown,"
                           f" invoked at {task.ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
