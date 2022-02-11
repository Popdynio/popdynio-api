from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
from popdyn import (
    Model,
    Transition
)

app = FastAPI()


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
    initial_population: dict
    transitions: List[TransitionRequest]


@app.post('/forecast')
def forecast(request: ForecastRequest):
    model = Model(request.ids)

    for transition in request.transitions:
        model[transition.source, transition.dest] = Transition(
            transition.alpha, transition.beta, *(transition.factors), N=transition.includes_n)

    initial_pop = list(request.initial_population.values())
    time, forecast = model.solve(
        t=request.forecast_time, initial_pop=initial_pop)

    forecast_response = {
        group: group_forecast.tolist() for (group, group_forecast) in zip(request.ids, forecast)
    }
    print(forecast_response)

    return {
        "time": time.tolist(),
        "forecast": forecast_response,
        "model_str": str(model)
    }
