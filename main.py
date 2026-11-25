import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from configuration.connections import DatabaseConnection

from typing import Literal

from service.twitch_service import get_twitch_data_specific_try


load_dotenv()

app = FastAPI()

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
host=os.getenv("host")
user=os.getenv("user")
password=os.getenv("password")
database=os.getenv("database")

# CREATE, READ, UPDATE, DELETE - USER

@app.get("/")
def root():
    return {"message": "API Twitch active"}


class UserCreate(BaseModel):
    username: str
    age: int = Field(..., ge=0, le=120)

@app.get("/users")
async def get_users():
    mydb = DatabaseConnection(
            host=host, user=user, password=password, database=database
        )
    connection = await mydb.get_db_connection()
    mycursor = connection.cursor()
    mycursor.execute("SELECT * FROM users")
    res = mycursor.fetchall()
    return res

@app.get("/user/{user_id}")
async def get_user(user_id: int):
    mydb = DatabaseConnection(
            host=host, user=user, password=password, database=database
        )
    connection = await mydb.get_db_connection()
    mycursor = connection.cursor()
    mycursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    res = mycursor.fetchall()
    if res == []:
        return {"message": "User not found" }
    
    return res

@app.post("/users")
async def post_user_validation(user: UserCreate):
    mydb = DatabaseConnection(
        host=host, user=user, password=password, database=database
    )
    connection = await mydb.get_db_connection()
    mycursor = connection.cursor()
    username = user.username
    age = user.age
    mycursor.execute(f'INSERT INTO `users`(username, age) VALUES ("{username}",{age});')
    connection.commit()
    return JSONResponse(content={"message": "User added successfully"}, status_code=201)

@app.put("/users/{user_id}")
async def update_user(user_id: int, user: UserCreate):
    mydb = DatabaseConnection(
        host=host, user=user, password=password, database=database
    )
    connection = await mydb.get_db_connection()
    mycursor = connection.cursor()
    username = user.username
    age = user.age
    update_fields = []
    if username:
        update_fields.append(f'username="{username}"')
    if age:
        update_fields.append(f"age={age}")
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    mycursor.execute(f'UPDATE `users` SET {", ".join(update_fields)} WHERE id={user_id};')
    connection.commit()
    if mycursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return JSONResponse(
        content={"message": "User updated successfully"}, status_code=200
    )

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    mydb = DatabaseConnection(
        host=host, user=user, password=password, database=database
    )
    connection = await mydb.get_db_connection()
    mycursor = connection.cursor()
    mycursor.execute(f"DELETE FROM users WHERE id = {user_id}")
    connection.commit()
    if mycursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return JSONResponse(
        content={"message": "User deleted successfully"}, status_code=200
    )

class StreamerReaction(BaseModel):
    user_id: int
    streamer_login: str
    reaction: Literal["like", "dislike"]

@app.post("/reactions")
async def save_reaction(data: StreamerReaction):
    mydb = DatabaseConnection(
            host=host, user=user, password=password, database=database
        )
    connection = await mydb.get_db_connection()
    mycursor = connection.cursor()

    streamer = get_twitch_data_specific_try(
        data.streamer_login, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
    )
    if "error" in streamer:
        raise HTTPException(status_code=404, detail=streamer["error"])

    streamer_id = streamer.get("id")
    streamer_login = streamer.get("login", data.streamer_login)
    mycursor.execute(
        f"SELECT id FROM streamer_reactions WHERE user_id = {data.user_id} AND streamer_id = '{streamer_id}'"
    )
    existing = mycursor.fetchone()

    if existing:
        mycursor.execute(
            f"UPDATE streamer_reactions SET reaction = '{data.reaction}', streamer_login = '{streamer_login}' WHERE user_id = {data.user_id} AND streamer_id = '{streamer_id}'"
        )
    else:
        mycursor.execute(
            f"INSERT INTO streamer_reactions (user_id, streamer_id, streamer_login, reaction) VALUES ({data.user_id}, '{streamer_id}', '{streamer_login}', '{data.reaction}')"
        )

    connection.commit()
    return JSONResponse(
        content={
            "message": "Reaction saved successfully",
            "user_id": data.user_id,
            "streamer_id": streamer_id,
            "streamer_login": streamer_login,
            "reaction": data.reaction,
        },
        status_code=201,
    )

@app.get("/reactions/{user_id}")
async def get_user_reactions(user_id: int):
    mydb = DatabaseConnection(
        host=host, user=user, password=password, database=database
    )
    connection = await mydb.get_db_connection()
    mycursor = connection.cursor()
    mycursor.execute(f"SELECT * FROM streamer_reactions WHERE user_id = {user_id}")
    res = mycursor.fetchall()
    return res

class PlaylistCreate(BaseModel):
    user_id: int
    name: str
    description: str | None = None


class PlaylistStreamerAdd(BaseModel):
    playlist_id: int
    streamer_login: str
    position: int = 1

@app.post("/playlists")
async def create_playlist(data: PlaylistCreate):
    mydb = DatabaseConnection(
        host=host, user=user, password=password, database=database
    )
    connection = await mydb.get_db_connection()
    mycursor = connection.cursor()

    desc_sql = f"'{data.description}'" if data.description else "NULL"
    mycursor.execute(
        f"INSERT INTO playlists (user_id, name, description) VALUES ({data.user_id}, '{data.name}', {desc_sql})"
    )
    connection.commit()
    return JSONResponse(
        content={
            "message": "Playlist created successfully",
            "id": mycursor.lastrowid,
            "user_id": data.user_id,
            "name": data.name,
        },
        status_code=201,
    )


@app.post("/playlists/streamers")
async def add_streamer_to_playlist(data: PlaylistStreamerAdd):
    mydb = DatabaseConnection(
        host=host, user=user, password=password, database=database
    )
    connection = await mydb.get_db_connection()
    mycursor = connection.cursor()

    streamer = get_twitch_data_specific_try(
        data.streamer_login, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
    )
    if "error" in streamer:
        raise HTTPException(status_code=404, detail=streamer["error"])

    streamer_id = streamer.get("id")
    streamer_login = streamer.get("login", data.streamer_login)
    mycursor.execute(
        f"INSERT INTO playlist_streamers (playlist_id, streamer_id, streamer_login, position) VALUES ({data.playlist_id}, '{streamer_id}', '{streamer_login}', {data.position})"
    )
    connection.commit()
    return JSONResponse(
        content={
            "message": "Streamer added to playlist",
            "playlist_id": data.playlist_id,
            "streamer_id": streamer_id,
            "streamer_login": streamer_login,
            "position": data.position,
        },
        status_code=201,
    )


@app.get("/playlists/user/{user_id}")
async def get_user_playlists(user_id: int):
    mydb = DatabaseConnection(
        host=host, user=user, password=password, database=database
    )
    connection = await mydb.get_db_connection()
    mycursor = connection.cursor(dictionary=True)

    mycursor.execute(
        f"SELECT id, user_id, name, description, created_at FROM playlists WHERE user_id = {user_id}"
    )
    playlists = mycursor.fetchall()

    for pl in playlists:
        mycursor.execute(
            f"SELECT streamer_id, streamer_login, position, added_at FROM playlist_streamers WHERE playlist_id = {pl['id']} ORDER BY position ASC"
        )
        pl["streamers"] = mycursor.fetchall()

    return playlists

@app.get("/twitch/{login}")
def get_streamer(login: str):
    data = get_twitch_data_specific_try(login, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
    if "error" in data:
        print(data)
        raise HTTPException(status_code=404, detail=data["error"])
    return JSONResponse(content=data, status_code=200)