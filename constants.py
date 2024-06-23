
EVENTS_DIR = 'events/'
IMAGES_DIR = 'images/'

EVENTS_FNAME = 'events_data.bin'

TOTAL_DAYS_WITH_EVENTS = 27

DATETIME_INPUT_FORMAT = "%H:%M %d.%m"

class BUTTON_NAMINGS:
	echo = "ECHO"
	create_event = "Создать мероприятие"
	get_events = "Список мероприятий"
	main_menu = "Главное меню"
	save_modified_event = "Сохранить мероприятие"
	decline_modified_event = "Вернуться в главное меню без сохраниения"
	change_event_name = "Изменить название"
	change_event_date = "Изменить дату и время"
	change_event_description = "Изменить описание"
	change_event_picture = "Изменить картинку"
	modify_event = "Редактировать мероприятие"
	remove_event = "Удалить мероприятие"


MISC_MESSAGES = {
	"event_naming" : "Введите название мероприятия",
	"event_dating" : f"Введите дату и время мероприятия в формате {DATETIME_INPUT_FORMAT}",
	"event_picturing" : "Отправьте фото мероприятия",
	"event_descriptioning" : "Отправьте описание мероприятия",
	}
