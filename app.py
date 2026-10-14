from pathlib import Path
import uvicorn
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import logging
from datetime import datetime
from starlette.responses import RedirectResponse
from utils.db_utils import connect_db
from utils.sql_reqsts import add_image, get_images_data, delete_image_data, get_image_name_for_delete
from utils.file_utils import is_allowed_file, MAX_UPLOAD_SIZE, get_unique_name


logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / "app.log"

PAGE_SIZE = 10

logging.basicConfig(
    level=logging.INFO,
    format="[{asctime}] - {name} - {levelname} - {message}",
    style="{",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logging.getLogger("watchfiles").setLevel(logging.WARNING)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница сервиса"""
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/images/", response_class=HTMLResponse)
async def images(request: Request,
        page:int = Query(ge=1, default=1)):
    """Страница с изображениями"""
    limit = PAGE_SIZE
    offset = (page - 1) * limit
    images_data_dict = []
    #запрос к БД (получаем на 1 элемент больше для проверки количества страница)
    try:
        images_data_dict = await connect_db(sql_reqst=get_images_data, params=(limit + 1, offset), fetch='all')
        logging.info(f'Успешный запрос к БД. Возвращено элементов: {len(images_data_dict)}')
    except Exception as e:
        logging.error(f'Ошибка при обращении к БД: {e}')

    #получаем базовый URL
    base_url = str(request.base_url).rstrip("/")

    #создаем полный URL для каждого изображения
    for img in images_data_dict:
        img["url"] = f"{base_url}/images/file/{img['filename']}"

    #определяем, есть ли страницы впереди и позади текущей
    has_next = len(images_data_dict) > limit
    has_prev = page > 1

    #если страница есть, срезаем доп. элемент
    if has_next:
        images_data_dict = images_data_dict[:limit]

    #возвращаем шаблон страницы
    return templates.TemplateResponse(
        request=request,
        name="images.html",
        context={
            "images":images_data_dict,
            "page":page,
            "has_next": has_next,
            "has_prev": has_prev
        }
    )


@app.get("/delete/{id}")
async def delete_image(id: int):
    """Удаление изображений"""
    #получаем имя файла
    try:
        db_response = await connect_db(sql_reqst=get_image_name_for_delete, params=(id, ), fetch='one')
        logging.info('Успешный запрос к БД')

        #получаем путь к файлу
        filename = db_response['filename']
        file_path = Path('images').joinpath(filename)

        #удаляем файл с диска
        if file_path.is_file():
            file_path.unlink()
            logging.info(f'Файл "{filename}" удален с сервера')
        else:
            logging.info(f'Файл "{filename}" не найден.')

        #удаляем данные о файле из БД
        try:
            await connect_db(sql_reqst=delete_image_data, params=(id, ), fetch=None)
        except Exception as e:
            logging.error(f'Ошибка удаления данных их БД: {e}')
        else:
            logging.info('Данные о файле удалены из БД')

    except Exception as e:
        logging.error(f'Ошибка удаления файла: {e}')

    #возвращаем шаблон страницы
    return RedirectResponse(url='/images/', status_code=302)



@app.get("/upload/", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Страница загрузки изображений"""
    return templates.TemplateResponse(request=request, name="upload.html", context={})


@app.post("/upload/")
async def upload(request: Request, file: UploadFile = File(...)):
    """Страница загрузки изображений. POST"""
    my_file = Path(file.filename)
    logging.info(f'Получен файл: {my_file}')

    #проверяем формат файла
    if not is_allowed_file(my_file):
        logging.error(f'Неподдерживаемый формат файла {my_file}')
        raise HTTPException(status_code=400, detail='Неподдерживаемый формат файла')

    #проверяем размер файла
    contents = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(contents) > MAX_UPLOAD_SIZE:
        logging.error(f'Файл{my_file} слишком большой')
        raise HTTPException(status_code=400, detail='Файл слишком большой')

    #получаем уникальное имя файла
    new_filename = get_unique_name(my_file)
    logging.info(f"New filename: {new_filename}")

    #сохраняем файл
    image_dir = Path("images")
    image_dir.mkdir(exist_ok=True)
    save_path = image_dir / new_filename
    save_path.write_bytes(contents)
    logging.info(f'Файл {save_path} сохранён')

    #определяем размер сохраненного файла
    file_size = Path(save_path).stat().st_size
    #данные для записи в БД
    params = (new_filename, str(my_file), file_size, datetime.now(), my_file.suffix.lower())

    #запись данных о файле в БД
    try:
        await connect_db(add_image, params, fetch=None)
    except Exception as e:
        logging.error(f'Ошибка записи метаданных в БД: {e}')
    else:
        logging.info(f'Метаданные файла {save_path} записаны в БД')

    #возвращаем шаблон страницы
    return templates.TemplateResponse(request=request, name="upload.html", context={})


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)