from .background_tasks import start_background_task


async def send_list(send, data_list):
    message = "```\n"
    column_counter = 0
    row = ""
    for key in data_list:
        if column_counter > 0:
            row += "    "
        if len(row) + len(key) > 42:
            column_counter = 0
            message += row + "\n"
            row = ""
        row += f"{key}"
        column_counter += 1
        if len(message) > 1950:
            column_counter = 0
            message += row + "\n"
            row = ""
        if len(message) > 1900:
            message += "```"
            await send(message)
            message = "```\n"
    message += row
    message += "```"
    await send(message)

