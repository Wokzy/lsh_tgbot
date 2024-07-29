
import sys
import pytz
import datetime

EVENTS_DIR = 'events/'
IMAGES_DIR = 'images/'

EVENTS_FNAME = 'events_data.bin'
KOMSA_LIST_FNAME = 'komsa.bin'
STATIC_DATA_FNAME = 'static_data.bin'

TOTAL_DAYS_WITH_EVENTS = 24 # Deprecated

TIMEZONE = pytz.timezone('Asia/Novosibirsk')
DATETIME_INPUT_FORMAT = "%H:%M %d"
DATETIME_HUMAN_FORMAT = "час:минута день (Пример: 14:00 24)"

DEBUG_MODE = '--debug' in sys.argv

DAILY_NEWSLETTER_TIME = datetime.time(7, 0, 0, 0, tzinfo=TIMEZONE)
KOMSA_CALL_COOLDOWN = datetime.timedelta(days=1)
KOMSA_CALL_REQUEST_EXPIRATION_TIME = datetime.timedelta(days=2)

if DEBUG_MODE:
	_debug_time = datetime.datetime.now()
	DAILY_NEWSLETTER_TIME = datetime.time(_debug_time.hour,
										_debug_time.minute + (_debug_time.second + 10 >= 60),
										(_debug_time.second + 10) % 60, 
										0,
										tzinfo=TIMEZONE)


class BUTTON_NAMINGS:
	echo                        = "ECHO"
	create_event                = "Создать мероприятие"
	get_events                  = "Список мероприятий"
	main_menu                   = "Главное меню"
	return_to_main_menu         = "Вернуться в главное меню"
	save_modified_event         = "Сохранить мероприятие"
	decline_modified_event      = "Вернуться в главное меню без сохраниения"
	change_event_name           = "Изменить название"
	change_event_date           = "Изменить дату и время"
	change_event_description    = "Изменить описание"
	change_event_picture        = "Изменить картинку"
	modify_event                = "Редактировать мероприятие"
	remove_event                = "Удалить мероприятие"
	confirm_removal             = "Подтвердить удаление"
	decline_removal             = "Не удалять"
	user_settings               = "Настройки"
	user_authorization          = "Пройти авторизацию"
	technical_support           = "Техническая поддержка"
	edit_newsletter             = "Дневная рассылка"
	canteen_menu                = "Меню"
	notify                      = "Напомнить"
	disnotify                   = "Не напоминать"
	update_komsa_description    = "Обновить своё описание (комса)"
	faq                         = "Часто задаваемые вопросы"
	faq_other_questions         = "Остальные вопросы"
	komsa_list                  = "Список комсы"
	call_komsa                  = "Пригласить этого комсёнка"
	confirm_call                = "Пригласить"
	decline_call                = "Не приглашать"
	additional_info             = "Указать дополнительную информацию"
	allow_call_tutor            = "Да, разрешаю"
	decline_call_tutor          = "Нет, я против"
	accept_call_root            = "Я приду"
	decline_call_root           = "Я не приду"
	edit_komsa_call_description = "Изменить описание"
	hide_event                  = "Скрыть мероприятие"
	reveal_event                = "Раскрыть мероприятие"


MISC_MESSAGES = {
	"event_naming" : "Введите название мероприятия",
	"event_dating" : f"Введите дату и время мероприятия в формате {DATETIME_HUMAN_FORMAT}",
	"event_picturing" : "Отправьте фото мероприятия",
	"event_descriptioning" : "Отправьте описание мероприятия",
	"removal_approvement": "Вы уверены в том, что хотите удалить данное мероприятие?",
	"user_authorization": "Введите информацию о себе в формате [класс] [Имя] [Фамилия] [код воспитателя (если вы воспет какого-то класса)]\n\nПример:\n9-2 Баульбек Баульбеков",
	"technical_support": "Связаться с разработчиком @Wokzy1 можно непосредственно в телеграмм",
	"wrong_auth_data": "Проверьте корректность введёных данных. Убедитесь, что это точно ваше имя, ваша фамилия и вы учитесь именно в этом классе",
	"edit_newsletter": "Если вы хотите изменить сообщение дневной рассылки, то просто отправьте новое (Прикрепляйте не более одного фото): ",
	"newsletter_changed": "Рассылка была успешно изменена",
	"edit_canteen_menu": "Если вы хотите редактировать меню, то просто отправьте новое",
	"canteen_menu_chaged": "Меню было успешно отредактировано",
	"update_komsa_description":"Отправьте своё новое описание, можно прикрепить одно фото",
	"update_komsa_description_success":"Вы успешно обновили информацию о себе",
	"faq":"Выберите вопрос:",
	"confirm_call":"Вы уверены, что хотите пригласить этого комсёнка? Прежде, чем он попадёт к вам, будет отправлен запрос на подтверждение вашим воспитателям класса. Если хотя бы один из них подтвердит вызов комсёнка, запрос на подтверждение будет отправлен самому комсёнку. Если на одном из этапов вызов будет прерван, вы будете уведомлены, иначе вы получите сообщение о грядущем прибытии комсёнка.",
	"residense_required":f"Прежде, чем воспользоваться данной функцией, пожалуйста укажите свой блок и общажитие. Это можно сделать в настройках в поле {BUTTON_NAMINGS.additional_info}",
	"call_komsa_description":"Отправьте дополнительную информацию: укажите желаемое место встречи (блок), если вы хотите вызвать несколько комсят, то сколько и каких",
	"hide_event":"Вы скрыли мероприятие от летнешкольников",
	"reveal_event":"Теперь это мероприятие смогут увидеть летнешкольники",
}

ROLE_MAPPING = {
	"user"  : "Ученик Летней школы",
	"tutor" : "Воспитатель",
	"root"  : "Комсёнок",
}


FAQ = [
	("queston1", "answer1"),
	("queston2", "answer2"),
]
