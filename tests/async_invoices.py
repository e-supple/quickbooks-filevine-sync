import os
import asyncio
from conductor import AsyncConductor
from dotenv import load_dotenv

load_dotenv()

conductor = AsyncConductor(
    api_key=os.environ.get("CONDUCTOR_SECRET_KEY"),  # This is the default and can be omitted
)


async def main() -> None:
    page = await conductor.qbd.invoices.list(
        conductor_end_user_id="end_usr_Wb4uG5P0SbiOmD",
    )
    print(page.data)


asyncio.run(main())