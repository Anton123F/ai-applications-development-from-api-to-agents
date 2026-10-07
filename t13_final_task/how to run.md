
before run command bellow , needs to actibate python .venv-wsl sandbox, => **source .venv-wsl/bin/activate** from root folder
from root run 
**PYTHONPATH=. python3 t13_final_task/task/agent/app.py**

UI app:
from t13_final_task> run: => **python -m http.server 8080** then open http://localhost:8080/task/index.html

## stop all images
- docker stop $(docker ps -q)
## stop and delete all data
- docker compose down -v