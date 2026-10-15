# Diver's License: Statistics API

A FastAPI service that returns min, max, average, median or 95th percentile of `pressure` or `velocity` over selected
outputs and parts of a simulation. The data is described as:
- users
  - 0
    - simulations
      - dambreak
        - output_0.hdf5
        - output_1.hdf5
        - output_2.hdf5
      - moving_cube
        - output_0.hdf5
        - output_1.hdf5
        - output_2.hdf5
  - 1
    - simulations
      - dambreak
        - output_0.hdf5
        - output_1.hdf5
        - output_2.hdf5

## Run

Needs Python 3.11+ and internet access. Run from the project root:
```
python -m pip install -r requirements.txt
python -m backend.auth 0
uvicorn backend.main:app --reload
```

`python -m backend.auth 0` prints an API token for user 0 (it's shown only once). The API runs at
http://127.0.0.1:8000. In the docs at http://127.0.0.1:8000/docs, click **Authorize** and paste the token.

## UI (optional)

Needs Node.js. In a second terminal:

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and paste the token into the "API token" field.

## Example

```
curl.exe -H "Authorization: Bearer <token>" "http://127.0.0.1:8000/users/0/simulations/dambreak/stats?attribute=velocity&stat=max&outputs=0,1,2&parts=fluid"
```

All endpoints and parameters are listed in `/docs`.

## Tests

```
python -m pytest                  # all tests
python -m pytest -m "not load"    # without the load test
```
