## IF2514302-Intro-To-AI-Final
Intro To AI Final Project Assignment
## Folder Structure
```
main
├── a_star
│   └──backend.py
├── data
│   ├── balikpapan_jalan.graphml
│   └── balikpapan_pois.gpkg
├── out
│   └── rute_optimal_final.geojson
├── index.html
└── README.md
```
- data:  
`balikpapan_jalan.graphml`: Used for geographic data processing inside the algorithm, containing balikpapan street graph
`balikpapan_pois.gpkg`: Used for determining location coordinate

- a_star:  
`backend.py`: the main logic behind this project, containing the a-star algorithm and the logic to solve multi route destinations

- static:
contains files relevant to the user interface via web

- templates:
contains index.html for interface structures

- `app.py`: main app. Using flask to run this project

## How to Run
- Make sure python version 3.15.x is installed. Using virtual env is preferred.
- run `pip install -r requirements.txt` on the project dir. Wait until pip downloads the required libs.
- Once pip is done, run `python app.py` to start the application.
- Open ip at the desired port on the web browser.