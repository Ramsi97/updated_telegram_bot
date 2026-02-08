from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware, types
from app.config import settings

class MembershipMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.Update,
        data: Dict[str, Any]
    ) -> Any:
        # Get user from event
        user = None
        if event.message:
            user = event.message.from_user
        elif event.callback_query:
            user = event.callback_query.from_user

        if not user:
            return await handler(event, data)

        # BYPASS 1: Check if user is in AUTHORIZED_USER_IDS (Admins)
        if user.id in settings.authorized_users:
            # print(f"DEBUG: User {user.id} is an authorized admin. Bypassing group check.")
            return await handler(event, data)

        # BYPASS 2: Check if group restriction is even active
        if not settings.REQUIRED_GROUP_ID:
            return await handler(event, data)

        try:
            # Check membership
            member = await event.bot.get_chat_member(
                chat_id=settings.REQUIRED_GROUP_ID,
                user_id=user.id
            )

            # Allowed statuses: owner, creator, administrator, member, restricted (still in group)
            if member.status in ["owner", "creator", "administrator", "member", "restricted"]:
                return await handler(event, data)
            
            # Not a member (left, kicked, or others)
            print(f"DEBUG: Access DENIED for user {user.id} (Status: {member.status})")
            
            restriction_msg = (
                "⚠️ This bot is only available for members of our official group.\n\n"
                "Please join the group first to use the service."
            )
            
            if event.message:
                await event.message.answer(restriction_msg)
            elif event.callback_query:
                await event.callback_query.answer(restriction_msg, show_alert=True)
            
            return # Block update
            
        except Exception as e:
            # If error (chat not found, etc.), BLOCK access and log it
            print(f"❌ Membership Error for User {user.id} in Chat {settings.REQUIRED_GROUP_ID}: {e}")
            
            error_msg = (
                "⚠️ Bot configuration error.\n"
                "The membership check failed. Please contact the administrator."
            )
            
            if user.id in settings.authorized_users:
                # Still allow admins to see the actual error for debugging
                debug_msg = (
                    f"🔬 [ADMIN DEBUG]\n"
                    f"Error: {e}\n"
                    f"Checking Group ID: `{settings.REQUIRED_GROUP_ID}`\n\n"
                    "Possible fixes:\n"
                    "1. Is the Group ID correct? (Must start with -100 for supergroups)\n"
                    "2. Is the bot IN that group as an Admin?\n"
                    "3. Did you rebuild Docker after changing .env?"
                )
                if event.message: await event.message.answer(debug_msg)
                return await handler(event, data)

            if event.message:
                await event.message.answer(error_msg)
            elif event.callback_query:
                await event.callback_query.answer(error_msg, show_alert=True)
            
            return # Block update to be safe
