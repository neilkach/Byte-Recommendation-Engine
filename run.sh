docker stop $(docker ps -a -q)
docker system prune -af
docker build -t rec-engine .
docker run -d -p 80:3000 rec-engine