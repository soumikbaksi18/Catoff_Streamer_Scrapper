from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from typing import List  
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = FastAPI()

class StreamRequest(BaseModel):
    game: str
    region: str
    platform: str  
    top: int  

# Function to fetch Twitch streams
def scrape_twitch_streams(game: str, region: str, top: int):
    driver = None  # Initialize driver variable
    try:
        # Use ChromeDriverManager to get the latest version of ChromeDriver
        chrome_driver_path = ChromeDriverManager().install()

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Running headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration
        chrome_options.add_argument("--disable-software-rasterizer")  # Disable software WebGL renderer
        chrome_options.add_argument("--disable-webgl")  # Disable WebGL
        chrome_options.add_argument("--force-device-scale-factor=1")
        chrome_options.add_argument("--disable-accelerated-2d-canvas")  # Disable GPU for 2D canvas
        chrome_options.add_argument("--disable-accelerated-compositing")  # Disable accelerated compositing
        
        # Initialize ChromeDriver with the Service object
        driver = webdriver.Chrome(service=Service(chrome_driver_path), options=chrome_options)
        
        url = f"https://www.twitch.tv/directory/game/{game.replace(' ', '%20')}"
        driver.get(url)

        # Wait for the streams container to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'ScThumbnailBrowse-thumbnail__image')]")))

        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        streams = []
        count = 0
        for stream in soup.find_all("div", class_="ScThumbnailBrowse-thumbnail__image"):  
            if count >= top:
                break
            title = stream.find("img")["alt"]
            link = stream.find_parent("a")["href"]
            streams.append({
                "title": title,
                "url": f"https://www.twitch.tv{link}"  
            })
            count += 1
        
        if not streams:
            raise Exception("No streams found on Twitch.")
        
        return streams

    except Exception as e:
        # Check if the driver was initialized, and quit if it was
        if driver:
            driver.quit()
        raise HTTPException(status_code=500, detail=f"Error while fetching Twitch streams: {str(e)}")
    finally:
        # Ensure the driver is quit in case of any other exceptions
        if driver:
            driver.quit()

# Function to fetch YouTube streams
def scrape_youtube_streams(game: str, top: int) -> List[dict]:
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        search_query = f"{game} live streams"
        url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '%20')}"
        driver.get(url)
        
        time.sleep(3)  

        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        streams = []
        count = 0
        for stream in soup.find_all("ytd-video-renderer"):
            if count >= top:
                break
            title_tag = stream.find("a", {"id": "video-title"})
            if title_tag:
                title = title_tag.get("title", "No title")
                link = "https://www.youtube.com" + title_tag.get("href", "")
                streams.append({
                    "title": title,
                    "url": link
                })
                count += 1
        
        if not streams:
            raise Exception("No live streams found.")
        
        driver.quit()  
        return streams

    except Exception as e:
        driver.quit()  
        raise Exception(f"An error occurred: {str(e)}")

@app.post("/scrape-streams/")
async def scrape_streams(request: StreamRequest):
    if request.platform.lower() == "twitch":
        if request.game.lower() == "valorant":
            return {"streams": scrape_twitch_streams("Valorant", request.region, request.top)}
        elif request.game.lower() == "csgo":
            return {"streams": scrape_twitch_streams("Counter-Strike: Global Offensive", request.region, request.top)}
        elif request.game.lower() == "clash of clans":
            return {"streams": scrape_twitch_streams("Clash of Clans", request.region, request.top)}
        else:
            raise HTTPException(status_code=400, detail="Game not supported for Twitch.")
    
    elif request.platform.lower() == "youtube":
        if request.game.lower() == "valorant":
            return {"streams": scrape_youtube_streams("Valorant", request.top)}
        elif request.game.lower() == "csgo":
            return {"streams": scrape_youtube_streams("Counter-Strike: Global Offensive", request.top)}
        elif request.game.lower() == "clash of clans":
            return {"streams": scrape_youtube_streams("Clash of Clans", request.top)}
        else:
            raise HTTPException(status_code=400, detail="Game not supported for YouTube.")
    
    else:
        raise HTTPException(status_code=400, detail="Platform not supported. Use 'Twitch' or 'YouTube'.")