Find the properly formatted guide on the Github Repo. https://github.com/ArchipelagoBrad/deadlockipelago/blob/main/local-deadlock-api/Self_Host_Guide.md
Unless you have software to format Markdown properly such as Obsidian the included file maybe more difficult to read on a local pc.

Useful Commands
docker compose -f deadlock-api-compose.yml start - Start the containers (Does Not Create)
docker compose -f deadlock-api-compose.yml stop - Stop the containers (Does Not Delete)
docker ps -a -f "name=deadlockapi" - See Status of any containers named deadlockapi (All 4 containers should have it as part of their name)