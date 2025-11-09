import asyncio

from researcharr.async_pipeline import IdentityStage, Pipeline


def test_async_context_manager_and_run_helper():
    async def agen():
        for i in range(3):
            yield i

    async def run_once():
        p = Pipeline()
        p.add_stage(IdentityStage(), concurrency=1, max_retries=0)
        # use run helper with async generator
        await p.run(agen())

    asyncio.run(run_once())
