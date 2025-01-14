import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from telegram.ext import CallbackContext

from constants import State
from repo.user import UserRepository

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup DB
user_repo = UserRepository()


# A dictionary to store user data temporarily during the setup
# todo: To be replace by DB
user_data = {
    'u_id': 2,
    'tx_id': 'test',
    'timings' : '00:00 - 00:00'
}

# Store group configurations
# todo: To be replace by DB and group ids
group_configs = {
    'Group1': {
        'eth_limit': 0.1,
        'sol_limit': 0.8,
        'blacklist': set()
    },
    'Group2': {
        'eth_limit': 0.1,
        'sol_limit': 0.8,
        'blacklist': set()
    }
}

async def start(update: Update, context: CallbackContext) -> State:
    """Handle the /start command."""
    logger.info(f"User {update.message.from_user.id} started the bot")
    user_repo.initiate_doc(tg_id = update.message.from_user.id)
    return await show_main_menu(update, context)

async def configure(update: Update, context: CallbackContext) -> State:
    """Handle the /configure command."""
    logger.info(f"User {update.message.from_user.id} configure the bot")
    user_repo.initiate_doc(tg_id = update.message.from_user.id)
    return await show_main_menu(update, context)

async def echo(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    user_text = update.message.text  # Get the user's message
    if update.message.chat.type in ['group', 'supergroup']:
        # Send the reply in DM (Direct Message) to the user
        user_id = update.message.from_user.id
        u_id = user_data['u_id']
        user_name = update.message.from_user.first_name
        await context.bot.send_message(u_id,
                                       f"""{user_name} Yes, working""")
    else:
        await update.message.reply_text(f"You said: {user_text}")

async def exit_conv(update: Update, context: CallbackContext) -> int:
    await update.callback_query.edit_message_text("👋👋👋 Goodbye! Use /start to restart the bot.👋👋👋")
    return ConversationHandler.END

async def back_to_main(update: Update, context: CallbackContext) -> State:
    """Handle the back to main menu button."""
    logger.info(f"User {update.callback_query.from_user.id} is returning to the main menu")
    await update.callback_query.answer()
    return await show_main_menu(update, context, is_new=False)

async def show_time(update: Update, context: CallbackContext) -> State:
    query = update.callback_query
    logger.info(f"User {str(query.from_user.id)[:4]}... is configuring time.")
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("⏰ Set Custom Time Slot", callback_data='set_time_slot')],
        [InlineKeyboardButton("🔄 Back to Main Menu", callback_data='back_to_main')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "⏰Time Configuration\n\n"
        f"Activate Time for the Bot (in UTC): {user_data['timings']}\n\n"
        "Choose an action:"
        "",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return State.SELECTING_BOT_TIME

async def time_slot_menu(update: Update, context: CallbackContext) -> State:
    """Ask user to enter a custom time slot."""
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Please enter a custom time slot in the format `HH:MM - HH:MM` (e.g., 09:00 - 18:00):",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return State.AWAITING_INPUT_TIME_SLOT

async def input_time_slot(update: Update, context: CallbackContext) -> State:
    """Handle user input for custom time slots."""
    user_input = update.message.text.strip()

    # Validate time slot format
    time_slot_pattern = r"^\d{2}:\d{2} - \d{2}:\d{2}$"
    if not re.match(time_slot_pattern, user_input):
        keyboard = [[InlineKeyboardButton("🔄 Cancel", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ Invalid format! Please enter a time slot in the format `HH:MM - HH:MM` (e.g., 09:00 - 18:00).",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return State.AWAITING_INPUT_TIME_SLOT

    # Store the valid time slot
    context.user_data['custom_time_slot'] = user_input
    user_data['timings'] = user_input

    # Confirm and return to the main menu
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Custom time slot set to: `{user_input}`",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return State.SELECTING_CONFIG

async def show_blacklist(update: Update, context: CallbackContext) -> State:
    """Show current blacklist and options."""
    query = update.callback_query
    await query.answer()

    group = context.user_data['selected_group']
    blacklist = group_configs[group]['blacklist']

    blacklist_text = "\n".join(blacklist) if blacklist else "No users in blacklist"

    keyboard = [
        [InlineKeyboardButton("➕ Add to Blacklist", callback_data='add_blacklist')],
        [InlineKeyboardButton("➖ Remove from Blacklist", callback_data='remove_blacklist')],
        [InlineKeyboardButton("🔄 Back", callback_data='back_to_group_options')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Blacklist for {group}\n\n"
        f"{blacklist_text}\n\n"
        "Choose an action:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return State.SETTING_BLACKLIST

async def handle_blacklist_update(update: Update, context: CallbackContext) -> State:
    """Handle adding or removing from blacklist."""
    handle = update.message.text.strip()
    if not handle.startswith('@'):
        handle = '@' + handle

    group = context.user_data['selected_group']
    action = context.user_data['blacklist_action']

    if action == 'add_blacklist':
        group_configs[group]['blacklist'].add(handle)
        message = f"✅ Added {handle} to blacklist"
    else:
        if handle in group_configs[group]['blacklist']:
            group_configs[group]['blacklist'].remove(handle)
            message = f"✅ Removed {handle} from blacklist"
        else:
            message = f"❌ {handle} was not in the blacklist"

    keyboard = [[InlineKeyboardButton("🔄 Back to Blacklist", callback_data='back_to_blacklist')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return State.SETTING_BLACKLIST

async def request_blacklist_handle(update: Update, context: CallbackContext) -> State:
    """Request Telegram handle for blacklist operation."""
    query = update.callback_query
    await query.answer()

    action = query.data
    context.user_data['blacklist_action'] = action

    keyboard = [[InlineKeyboardButton("🔄 Cancel", callback_data='cancel_blacklist')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Please enter the Telegram handle to {'add to' if action == 'add_blacklist' else 'remove from'} the blacklist:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return State.AWAITING_BLACKLIST_ADD if action == 'add_blacklist' else State.AWAITING_BLACKLIST_REMOVE

async def set_new_limit(update: Update, context: CallbackContext) -> State:
    """Handle the new limit value."""
    try:
        new_limit = float(update.message.text)
        logger.info(f"User {update.message.from_user.id} entered new limit: {new_limit}")
        if new_limit < 0:
            raise ValueError("Limit must be positive")

        group = context.user_data['selected_group']
        limit_type = context.user_data['setting_limit']

        if limit_type == 'set_eth_limit':
            group_configs[group]['eth_limit'] = new_limit
        else:
            group_configs[group]['sol_limit'] = new_limit

        keyboard = [[InlineKeyboardButton("🔄 Back to Limits", callback_data='set_limits')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Limit Updated Successfully!\n\n"
            f"New {'ETH' if limit_type == 'set_eth_limit' else 'SOL'} limit: {new_limit}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return State.SETTING_LIMITS

    except ValueError:
        await update.message.reply_text(
            "Please enter a valid positive number.",
            parse_mode="Markdown"
        )
        return State.AWAITING_ETH_LIMIT

async def request_limit(update: Update, context: CallbackContext) -> State:
    """Request new limit value from user."""
    query = update.callback_query
    logger.info(f"User {str(query.from_user.id)[:4]}... is setting a new limit.")
    await query.answer()

    limit_type = query.data
    context.user_data['setting_limit'] = limit_type

    keyboard = [[InlineKeyboardButton("🔄 Cancel", callback_data='cancel_limit_setting')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Please enter the new ETH limit as a number:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return State.AWAITING_ETH_LIMIT

async def show_limits(update: Update, context: CallbackContext) -> State:
    """Show current limits and options to set new ones."""
    query = update.callback_query
    logger.info(f"User {str(query.from_user.id)[:4]}... is viewing current limits.")
    await query.answer()

    print(context.user_data['selected_group'])
    group = context.user_data['selected_group']
    config = group_configs[group]

    keyboard = [
        [InlineKeyboardButton("Set ETH Limit(for base chain)", callback_data='set_eth_limit')],
        [InlineKeyboardButton("🔄 Back", callback_data='back_to_group_options')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Current Limits for {group}\n\n"
        f"ETH Limit(for base chain): {config['eth_limit']}\n"
        "Select an option to modify:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return State.SETTING_LIMITS

async def show_group_options(update: Update, context: CallbackContext) -> State:
    """Show options for the selected group."""
    query = update.callback_query
    logger.info(f"User {str(query.from_user.id)[:4]}... is viewing group options.")
    await query.answer()


    if query.data in ['Group1', 'Group2']:
        grp_ch = query.data
        context.user_data['selected_group'] = grp_ch
    elif context.user_data['selected_group'] in ['Group1', 'Group2']:
        grp_ch = context.user_data['selected_group']
        context.user_data['selected_group'] = grp_ch

    print(context.user_data['selected_group'])
    keyboard = [
        [InlineKeyboardButton("💰 Set Limits", callback_data='set_limits')],
        [InlineKeyboardButton("🚫 Set Blacklist", callback_data='set_blacklist')],
        [InlineKeyboardButton("🔄 Back", callback_data='back_to_groups')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"{grp_ch} Configuration\n\n"
        "Choose what you want to configure:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return State.SELECTING_GROUP_OPTIONS

async def configure_groups(update: Update, context: CallbackContext) -> State:
    """Start the group configuration."""
    query = update.callback_query
    logger.info(f"User {str(query.from_user.id)[:4]}... is configuring groups.")
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🔒 Group1", callback_data="Group1"),
         InlineKeyboardButton("🔓 Group2", callback_data="Group2")],
        [InlineKeyboardButton("🔄 Back to Main Menu", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Group Configuration\n\n"
        "Select the group you want to configure:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return State.SELECTING_GROUP

async def show_main_menu(update: Update, context: CallbackContext, is_new: bool = True) -> State:
    """Show the main menu with all options."""
    logger.info("Displaying the main menu")
    keyboard = [
        [InlineKeyboardButton("🚀 Configure Groups", callback_data='configure_groups')],
        [InlineKeyboardButton("⏰ Configure Activation Timings", callback_data='configure_timings')],
        [InlineKeyboardButton("🔑 Wallet Generate", callback_data='gen_eth_wallet')],
        [InlineKeyboardButton("📊 Current Status", callback_data='status')],
        [InlineKeyboardButton("🔚 Exit", callback_data='exit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Welcome to AixTG Bot. You sleep, I ape!\n\nPlease choose an option below:"

    if is_new:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return State.SELECTING_CONFIG


def main() -> None:
    """Run the bot."""
    # todo To be replaced by TG bot token
    application = Application.builder().token("YOUR_BOT_TOKEN").build()

    states_in = {

        State.SELECTING_CONFIG: [
            CallbackQueryHandler(configure_groups, pattern="^configure_groups$"),
            CallbackQueryHandler(show_time, pattern="^configure_timings$"),
            CallbackQueryHandler(exit_conv, pattern="^exit$"),
            # CallbackQueryHandler(gen_eth_wallet, pattern="^gen_eth_wallet"),
            # CallbackQueryHandler(menu_option, pattern="^status"),
            CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
        ],
        State.SELECTING_GROUP: [
            CallbackQueryHandler(show_group_options, pattern="^(Group1|Group2)$"),
            CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
        ],
        State.SELECTING_GROUP_OPTIONS: [
            CallbackQueryHandler(show_limits, pattern="^set_limits$"),
            CallbackQueryHandler(show_blacklist, pattern="^set_blacklist$"),
            CallbackQueryHandler(configure_groups, pattern="^back_to_groups$")
        ],
        State.SELECTING_BOT_TIME: [
            CallbackQueryHandler(time_slot_menu, pattern="set_time_slot"),
            CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
        ],
        State.SETTING_LIMITS: [
            CallbackQueryHandler(request_limit, pattern="^set_eth_limit$"),
            CallbackQueryHandler(show_limits, pattern="^set_limits$"),
            CallbackQueryHandler(show_group_options, pattern="^back_to_group_options$")
        ],
        State.SETTING_BLACKLIST: [
            CallbackQueryHandler(request_blacklist_handle, pattern="^(add|remove)_blacklist$"),
            CallbackQueryHandler(show_group_options, pattern="^back_to_group_options$"),
            CallbackQueryHandler(show_blacklist, pattern="^back_to_blacklist$")
        ],
        State.AWAITING_ETH_LIMIT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, set_new_limit),
            CallbackQueryHandler(show_limits, pattern="^cancel_limit_setting$")
        ],
        State.AWAITING_BLACKLIST_ADD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_blacklist_update),
            CallbackQueryHandler(show_blacklist, pattern="^cancel_blacklist$")
        ],
        State.AWAITING_BLACKLIST_REMOVE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_blacklist_update),
            CallbackQueryHandler(show_blacklist, pattern="^cancel_blacklist$")
        ],
        State.AWAITING_INPUT_TIME_SLOT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, input_time_slot),
            CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
        ],
    }

    # Create the conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start),
                      CommandHandler("configure", configure)],
        states = states_in ,
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.run_polling()

if __name__ == '__main__':
    main()