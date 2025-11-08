from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    username = State()
    password = State()


class SponsorStates(StatesGroup):
    handle = State()
    link = State()


class RedeemStates(StatesGroup):
    awaiting_redeem_code = State()


class DownloadStates(StatesGroup):
    waiting_for_quality = State()
    waiting_for_subtitle_choice = State()
    waiting_for_subtitle_lang = State()


