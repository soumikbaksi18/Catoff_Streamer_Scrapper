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

app = FastAPI()

class StreamRequest(BaseModel):
    game: str
    region: str
    platform: str  
    top: int  

def scrape_twitch_streams(game: str, region: str, top: int) -> List[dict]:
    url = f"https://www.twitch.tv/directory/game/{game.replace(' ', '%20')}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    streams = []
    count = 0
    for stream in soup.find_all("div", class_="stream"):
        if count >= top:
            break
        title = stream.find("h3").text
        link = stream.find("a")["href"]
        streams.append({
            "title": title,
            "url": f"https://www.twitch.tv{link}"
        })
        count += 1
    return streams

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
