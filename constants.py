
import datetime

EVENTS_DIR = 'events/'
IMAGES_DIR = 'images/'

EVENTS_FNAME = 'events_data.bin'
USERS_FNAME = 'users.bin'

TOTAL_DAYS_WITH_EVENTS = 24 # Deprecated

DATETIME_INPUT_FORMAT = "%H:%M %d.%m"

DAILY_NEWSLETTER_TIME = datetime.time(7, 0, 0, 0)

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
	confirm_removal = "Подтвердить удаление"
	decline_removal = "Не удалять"
	user_settings = "Настройки"
	user_authorization = "Пройти авторизацию"


MISC_MESSAGES = {
	"event_naming" : "Введите название мероприятия",
	"event_dating" : f"Введите дату и время мероприятия в формате {DATETIME_INPUT_FORMAT}",
	"event_picturing" : "Отправьте фото мероприятия",
	"event_descriptioning" : "Отправьте описание мероприятия",
	"removal_approvement": "Вы уверены в том, что хотите удалить данное мероприятие?",
	"user_authorization": "Введите информацию о себе в формате [класс] [Фамилия] [Имя] [код воспитателя (если вы воспет какого-то класса)]\n\nПример:\n9-2 Баульбек Баульбеков",
	"technical_support": "Связаться с разработчиком @Wokzy1 можно непосредственно в телеграмм",
	"wrong_auth_data":"Проверьте корректность введёных данных. Убедитесь, что это точно ваше имя, ваша фамилия и вы учитесь именно в этом классе",
	}
