from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from popdyn import (
    Model,
    Transition
)
from fastapi.openapi.utils import get_openapi

origins = ['*']
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

def cut_every(list, every, formatter):
    return [formatter(val) for i, val in enumerate(list) if i % every == 0]

class SolverMethod(Enum):
    ode = 'ODE'
    gillespie = 'Gillespie'
    tauleaping = 'TauLeaping'


class TransitionRequest(BaseModel):
    source: str = Field(..., example='S')
    dest: str = Field(..., example='I')
    alpha: float = Field(..., example=0.7)
    factors: List[str] = Field(..., example=['S', 'I'])
    includes_n: bool = Field(..., example=True)


class ForecastRequest(BaseModel):
    ids: List[str] = Field(..., example=['S', 'I', 'R'])
    forecast_time: int = Field(..., example=100)
    initial_population: List[int] = Field(..., example=[100, 1, 0])
    transitions: List[TransitionRequest]
    method: SolverMethod
    cut_every: Optional[int] = 1


@app.get('/')
def hello():
    return {'msg': 'Hello from popdynio-api'}


@app.post('/forecast')
def forecast(request: ForecastRequest):
    try:
        model = Model(request.ids)

        for transition in request.transitions:
            model[transition.source, transition.dest] = Transition(
                transition.alpha, *(transition.factors), N=transition.includes_n)

        if request.method == SolverMethod.ode:
            method = 'ODE'
        elif request.method == SolverMethod.tauleaping:
            method = 'TauLeaping'
        elif request.method == SolverMethod.gillespie:
            method = 'Gillespie'

        results = model.solve(
            t=request.forecast_time, initial_pop=request.initial_population, solver=method)

        time = cut_every(results['time'].tolist(), request.cut_every, lambda x: x)

        forecast = {}
        for group in request.ids:
            forecast[group] = cut_every(results[group].tolist(), request.cut_every, lambda x: format(x, '.2f'))

        response = {
            'time': time,
            'forecast': forecast,
            'model_str': str(model),
        }

        if method == 'ODE':
            diff_response = { i: {} for i in request.ids }
            in_out_transitions_groups = [model.get_in_out_trans(i) for i in request.ids]
            for (in_out_transitions, group) in zip(in_out_transitions_groups, request.ids):
                ins, outs = in_out_transitions
                diff_response[group]['in'] = [
                    {
                        'includes_n': in_transition.N,
                        'alpha': in_transition.rate,
                        'factors': in_transition.vars
                    }
                    for in_transition in ins
                ]
                diff_response[group]['out'] = [
                    {
                        'includes_n': out_transition.N,
                        'alpha': out_transition.rate,
                        'factors': out_transition.vars
                    }
                    for out_transition in outs
                ]
            response['diff_response'] = diff_response

        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Popdynio API",
        version="1.0.0",
        description="This is the API service for the Popdynio package",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
