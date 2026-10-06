import psycopg
from psycopg.rows import dict_row


async def connect_db(sql_reqst: str,params: tuple, fetch: str):
    async with await psycopg.AsyncConnection.connect(
        host="postgres",
        port=5432,
        dbname="image_storage",
        user='app_user',
        password='password',
        row_factory=dict_row
    ) as connection:

        async with connection.cursor() as cursor:
            await cursor.execute(sql_reqst, params)
            if fetch == 'one':
                return await cursor.fetchone()
            elif fetch == 'all':
                return await cursor.fetchall()

            return None


# asyncio.run(connect_db(sql_reqst, params, fetch=None))