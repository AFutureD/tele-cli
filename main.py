from telethon import TelegramClient, types
import asyncio
import typing

api_id = 5296356
api_hash = "5c7796703631d9c80cb53ba6ffc53a05"
client = TelegramClient("Inston3", api_id, api_hash)


async def main():
    async with client:
        # Getting information about yourself
        me = await client.get_me()

        # "me" is a user object. You can pretty-print
        # any Telegram object with the "stringify" method:
        print(me.stringify())

        if not isinstance(me, types.User):
            return

        print(me.username)
        print(me.phone)

        # You can print all the dialogs/conversations that you are part of:
        async for dialog in client.iter_dialogs():
            print(dialog.name, "has ID", dialog.id)

        # You can send messages to yourself...
        await client.send_message("me", "Hello, myself!")
        # ...to some chat ID
        await client.send_message(-5173099754, "Hello, group!")
        # ...to your contacts
        # await client.send_message('+8615757581109', 'Hello, friend!')
        await client.send_message(265113092, "Hello, friend ~")
        await client.send_message("AFuture", "Testing Telethon!")

        # You can, of course, use markdown in your messages:
        message = await client.send_message(
            "me",
            "This message has **bold**, `code`, __italics__ and a [nice website](https://example.com)!",
            link_preview=False,
        )

        # Sending a message returns the sent message object, which you can use
        print(message.raw_text)  # type: ignore[attr-defined]

        # You can reply to messages directly if you have a message object
        await message.reply("Cool!")  # type: ignore[attr-defined]

        # Or send files, songs, documents, albums...
        await client.send_file("me", "/Users/huanan/Downloads/0.jpg")

        # You can print the message history of any chat:
        async for message in client.iter_messages("me"):
            print(message.id, message.text)

            # You can download media from messages, too!
            # The method will return the path where the file was saved.
            if message.photo:
                path = await message.download_media()
                print("File saved to", path)  # printed after download is done


if __name__ == "__main__":
    asyncio.run(main())
