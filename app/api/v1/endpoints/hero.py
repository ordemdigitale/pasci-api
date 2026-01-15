# create: POST
# read: GET
# update: PATCH
# delete: DELETE
import slugify
from fastapi import APIRouter, HTTPException, status, Depends, Form
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List

from app.database.session import get_db
from app.schemas.hero import(
  TeamCreate,
  TeamRead,
  TeamReadWithHeroes,
  TeamUpdate,
  HeroCreate,
  HeroRead,
  HeroReadWithTeam,
  HeroUpdate
)
from app.models.hero import Team, Hero

hero_router = APIRouter()

######################
# Team Endpoints
######################
# create: POST
@hero_router.post("/teams", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(
  name: str = Form(...),
  db: AsyncSession = Depends(get_db)
) -> Team:
  # create the db record
  team_create = Team(
    name=name
  )
  # check for duplicate team name
  result = await db.execute(
    select(Team).where(Team.name == team_create.name)
  )
  existing_team = result.scalars().first()
  if existing_team:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail={
        "type": "duplicate_error",
        "errors": [
          {
            "field": "name",
            "message": "Une team avec ce nom existe déjà. Veuillez choisir un nom différent."
          }
        ]
      }
    )
  try:
    db_team = Team(**team_create.model_dump())
    db.add(db_team)
    await db.commit()
    await db.refresh(db_team)
    return db_team
  except Exception as e:
    await db.rollback()
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail={
        "type": "database_error",
        "errors": [
          {
            "field": "database",
            "message": f"Erreur lors de la création: {str(e)}"
          }
        ]
      }
    )

# read: GET
## read all
@hero_router.get("/teams", response_model=list[TeamReadWithHeroes], status_code=status.HTTP_200_OK)
async def get_teams(db: AsyncSession = Depends(get_db)):
  result = await db.execute(
    select(Team).options(selectinload(Team.heroes))
  )
  teams = result.scalars().all()
  return teams
## read single
@hero_router.get("/teams/{team_slug}", response_model=list[TeamReadWithHeroes], status_code=status.HTTP_200_OK)
async def get_team(team_slug: str, db: AsyncSession = Depends(get_db)):
  #result = await db.execute(select(RegionCiv).order_by(desc(RegionCiv.name)))
  result = await db.execute(
    select(Team).options(selectinload(Team.heroes)).where(Team.slug == team_slug)
  )
  team = result.scalars().first()
  return team

# update: PATCH
@hero_router.patch("/teams/{team_slug}", response_model=TeamReadWithHeroes, status_code=status.HTTP_200_OK)
async def update_team(team_slug: str, team_update: TeamUpdate, db: AsyncSession = Depends(get_db)):
  # fetch existing resource by slug
  result = await db.execute(
    select(Team).where(Team.slug == team_slug).options(selectinload(Team.heroes))
  )
  team = result.scalars().first()
  if not team:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team non trouvée.")
  # extract fields provided in the request (exclude unset ones)
  update_data = team_update.model_dump(exclude_unset=True)
  # update the database object attributes
  for key, value in update_data.items():
    setattr(team, key, value)
  # update slug if name changed
  if "name" in update_data:
     team.slug = slugify.slugify(team.name)

  # persist changes
  await db.commit()
  await db.refresh(team)
  return team

# delete: DELETE
@hero_router.delete("/teams/{team_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(team_slug: str, db: AsyncSession = Depends(get_db)):
  """ Delete a Team """
  # find team by slug
  result = await db.execute(select(Team).where(Team.slug == team_slug))
  team = result.scalar_one_or_none()
  # raise 404 if team does not exist
  if not team:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"Team {team_slug} not found."
    )
  await db.delete(team)
  await db.commit()
  return None

######################
# Hero Endpoints
######################
# create: POST
@hero_router.post("/hero", response_model=HeroRead, status_code=status.HTTP_201_CREATED)
async def create_hero(
  name: str = Form(...),
  team_id: str = Form(""),
  db: AsyncSession = Depends(get_db)
):
  # convert empty strings to None
  team_id_int = int(team_id) if team_id and team_id != "" else None
  # create the db record
  hero_create = Hero(
    name=name,
    team_id=team_id_int
  )
  # check for duplicate hero name
  result = await db.execute(select(Hero).where(Hero.name == hero_create.name))
  existing_hero = result.scalars().first()
  if existing_hero:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail={
        "type": "duplicate_error",
        "errors": [
          {
            "field": "name",
            "message": f"le héro {existing_hero.name} existe déjà. Veuillez choisir un nom différent."
          }
        ]
      }
    )
  try:
    db_hero = Hero(**hero_create.model_dump())
    db.add(db_hero)
    await db.commit()
    await db.refresh(db_hero)
    return db_hero
  except Exception as e:
    await db.rollback()
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail={
        "type": "database_error",
        "errors": [
          {
            "field": "database",
            "message": f"Erreur lors de la création du héro: {str(e)}"
          }
        ]
      }
    )

# read: GET
## read all
@hero_router.get("/heroes", response_model=list[HeroReadWithTeam], status_code=status.HTTP_200_OK)
async def get_heroes(db: AsyncSession = Depends(get_db)):
  result = await db.execute(
    select(Hero).options(joinedload(Hero.team))
  )
  heroes = result.scalars().all()
  return heroes

## read single
@hero_router.get("/heroes/{team_slug}", response_model=list[TeamReadWithHeroes], status_code=status.HTTP_200_OK)
async def get_hero(team_slug: str, db: AsyncSession = Depends(get_db)):
  #result = await db.execute(select(RegionCiv).order_by(desc(RegionCiv.name)))
  result = await db.execute(
    select(Team).options(selectinload(Team.heroes)).where(Team.slug == team_slug)
  )
  team = result.scalars().all()
  return team

# update: PATCH
@hero_router.patch("/heroes/{team_slug}", response_model=TeamReadWithHeroes, status_code=status.HTTP_200_OK)
async def update_hero(team_slug: str, team_update: TeamUpdate, db: AsyncSession = Depends(get_db)):
  # fetch existing resource by slug
  result = await db.execute(
    select(Team).where(Team.slug == team_slug).options(selectinload(Team.heroes))
  )
  team = result.scalars().first()
  if not team:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team non trouvée.")
  # extract fields provided in the request (exclude unset ones)
  update_data = team_update.model_dump(exclude_unset=True)
  # update the database object attributes
  for key, value in update_data.items():
    setattr(team, key, value)
  # update slug if name changed
  if "name" in update_data:
     team.slug = slugify.slugify(team.name)

  # persist changes
  await db.commit()
  await db.refresh(team)
  return team

# delete: DELETE
@hero_router.delete("/heroes/{team_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hero(team_slug: str, db: AsyncSession = Depends(get_db)):
  """ Delete a Team """
  # find team by slug
  result = await db.execute(select(Team).where(Team.slug == team_slug))
  team = result.scalar_one_or_none()
  # raise 404 if team does not exist
  if not team:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"Team {team_slug} not found."
    )
  await db.delete(team)
  await db.commit()
  return None