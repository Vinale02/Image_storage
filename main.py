from pathlib import Path
import uvicorn
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
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
async def images(request: Request):
    """Страница с изображениями"""
    try:
        images_data_dict = await connect_db(sql_reqst=get_images_data, params=None, fetch='all')
    except Exception as e:
        logging.error(f'Ошибка при обращении к БД: {e}')

    return templates.TemplateResponse(request=request, name="images.html", context={"images":images_data_dict})


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

    return RedirectResponse(url='/images/', status_code=302)
    # return {"message": "Элемент успешно удалён", "deleted_id": id}





@app.get("/upload/", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Страница загрузки изображений"""
    return templates.TemplateResponse(request=request, name="upload.html", context={})


@app.post("/upload/")
async def upload(request: Request, file: UploadFile = File(...)):
    """Страница загрузки изображений. POST"""
    my_file = Path(file.filename)
    logging.info(f'Получен файл: {my_file}')

    if not is_allowed_file(my_file):
        logging.error(f'Неподдерживаемый формат файла {my_file}')
        raise HTTPException(status_code=400, detail='Неподдерживаемый формат файла')

    contents = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(contents) > MAX_UPLOAD_SIZE:
        logging.error(f'Файл{my_file} слишком большой')
        raise HTTPException(status_code=400, detail='Файл слишком большой')

    new_filename = get_unique_name(my_file)
    logging.info(f"New filename: {new_filename}")

    image_dir = Path("images")
    image_dir.mkdir(exist_ok=True)
    save_path = image_dir / new_filename
    save_path.write_bytes(contents)
    logging.info(f'Файл {save_path} сохранён')

    file_size = Path(save_path).stat().st_size
    params = (new_filename, str(my_file), file_size, datetime.now(), my_file.suffix.lower())

    try:
        await connect_db(add_image, params, fetch=None)
    except Exception as e:
        logging.error(f'Ошибка записи метаданных в БД: {e}')
    else:
        logging.info(f'Метаданные файла {save_path} записаны в БД')

    return templates.TemplateResponse(request=request, name="upload.html", context={})


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)