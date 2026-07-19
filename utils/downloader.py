import uuid
from pathlib import Path

class Downloader:
    def __init__(self,
                downloader_page,
                queue,
                db_queue):
        self.page = downloader_page
        self.queue = queue
        self.db_queue=  db_queue

    async def download(self):
        save_folder = Path(__file__).resolve().parent.parent / "pictures"
        save_folder.mkdir(parents=True, exist_ok=True)
        print('save_folder')
        while True:
            item = await self.queue.get()
            if item == None:
                await self.db_queue.put(None)
                print('downloader finished')
                break
            files_path = []
            images_url = item.images_href
            print('image_url getted')
            for image_url in images_url:
                file_name = f"{uuid.uuid4()}.jpg"
                file_path = save_folder / file_name
                print('path made')
                files_path.append(file_path)
                response = await self.page.goto(image_url)
                image = await response.body()
                print('entered')
                with open(file_path, 'wb') as file:
                    file.write(image)
            item.images_path = [str(path) for path in files_path]
            await self.db_queue.put(item)

        

