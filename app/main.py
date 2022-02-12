from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from popdyn import (
    Model,
    Transition
)

origins = ["*"]
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TransitionRequest(BaseModel):
    source: str
    dest: str
    alpha: int
    beta: float
    factors: List[str]
    includes_n: bool


class ForecastRequest(BaseModel):
    ids: List[str]
    forecast_time: int
    initial_population: List[int]
    transitions: List[TransitionRequest]


@app.get('/')
def hello():
    return {'msg': 'Hello from popdynio-api'}


@app.post('/forecast')
def forecast(request: ForecastRequest):
    model = Model(request.ids)

    for transition in request.transitions:
        model[transition.source, transition.dest] = Transition(
            transition.alpha, transition.beta, *(transition.factors), N=transition.includes_n)

    time, forecast = model.solve(
        t=request.forecast_time, initial_pop=request.initial_population)

    forecast_response = {
        group: group_forecast.tolist() for (group, group_forecast) in zip(request.ids, forecast)
    }
    print(forecast_response)

    return {
        'time': time.tolist(),
        'forecast': forecast_response,
        'model_str': str(model)
    }
