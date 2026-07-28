# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import sql


def column_exists(cr, table_name, column_name):
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s
          AND column_name = %s
        """,
        (table_name, column_name),
    )
    return bool(cr.fetchone())


def pre_init_hook(env):
    cr = env.cr
    table_name = "fsm_location"
    column_name = "customer_id"

    if not column_exists(cr, table_name, column_name):
        cr.execute(
            sql.SQL('ALTER TABLE {table} ADD COLUMN {column} INT').format(
                table=sql.Identifier(table_name),
                column=sql.Identifier(column_name),
            )
        )

    cr.execute(
        sql.SQL(
            """
            UPDATE {table}
            SET {column} = owner_id
            WHERE {column} IS NULL
            """
        ).format(
            table=sql.Identifier(table_name),
            column=sql.Identifier(column_name),
        )
    )