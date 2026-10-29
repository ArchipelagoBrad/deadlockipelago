# Self Hosted Deadlock-API Instructions

This guide will allow you to self host Deadlock-API locally allowing you to no longer be rate-limited.

---

## Prerequisite

- Docker Engine

> This requires the docker engine to already be installed on your pc. If it is not you must install it yourself this guide will not go into details. [Docker Desktop Guide Here](https://docs.docker.com/desktop/setup/install/windows-install/). [Docker CLI here](https://docs.docker.com/engine/install/).

> **NOTE:** Docker Desktop is the GUI software. It automatically installs the Command Line Interface (CLI) as well. Docker CLI is just the CLI. This guide only uses CLI commands but CLI is only available on Windows Subsystem for Linux (WSL) or Linux (generally) so Docker Desktop is the easiest way to install it for both OSes but the GUI itself won't be used.

- Docker/Terminal Knowledge

> Its a minor amount of knowledge just how to use a terminal and how to use docker but even then its more do you even have it installed as this gives pretty handholdy instructions.

- deadlock-api-compose.yml & api.env

> This should be included in the Self-Host zip. Do not adjust the compose or env file its pre-configured with values that can cause other services to mess-up on if changed.

- local-deadlock-api-ingest

> This is a local version of deadlock-api-ingest it should be included in the Self-Host zip.

- deadlock-api-ingest

> This is the standard deadlock-api-ingest. It's recommended to run the primary one as well as it will send matches to deadlock-api.com which the AP will use as a back-up if your local version can't find the match. [Download it from its own repo](https://github.com/deadlock-api/deadlock-api-ingest).

- Extra Resources Available

> The Docker Engine does set up an VM for linux by default it reserves ~4gb of RAM for it and its containers. The containers only use ~100-300mb of RAM themselves but as the 4gb are reserved they are not available for the PC to use even if actively not in use. Due to this if you do not have extra RAM available it's unrecommended to self-host deadlock-api.

---

## First Time Setup

These instructions are for the very first time you set up the local instance so you should only need to do this once or only if you ever delete the containers and need to set it up again.

### Step 1 - Open A Terminal

Within a terminal navigate to where deadlock-api-compose.yml and api.env are downloaded.

### Step 2 - Run a few commands in terminal in order

`docker compose -f deadlock-api-compose.yml up -d` This creates the 4 needed containers.

`docker ps -a -f "name=deadlockapi"` This should list 4 containers. All should begin with "deadlockapi-" and it should be api-1, redis-1, clickhouse-1, and postgres-1. It should show that api-1 has the status of Exited (1) while the rest are healthy. Its exited because theres a missing user account it needs so the next commands make the user.

`docker exec -it deadlockapi-clickhouse-1 clickhouse-client` This enters clickhouse software on the clickhouse container for the next 2 commands.

`CREATE USER IF NOT EXISTS api_readonly_user IDENTIFIED BY 'localrestrictedpw';` This is executed within the container. Its creating a user called "api_readonly_user" with a password of "localrestrictedpw". After it is done it should say something like the following.

```sql
CREATE USER IF NOT EXISTS api_readonly_user IDENTIFIED BY 'localrestrictedpw'

Query id: xxxxxx-xxxxx-xxxx-xxx (A query id would be here).

Ok.

0 rows in set. Elapsed: 0.002 sec.
```

`GRANT SELECT ON default.* TO api_readonly_user;` Gives permissions to read the databases to the user we just created. Respone should be similar to above just with the "GRANT" command instead of "CREATE".

`exit` Just exits the container and should be back to a regular terminal.

`docker restart deadlockapi-api-1` This restarts the API specifically as it needs to be restarted to realize that clickhouse is now set-up properly.

### Step 3 - Thats it

Its genuienly just that.
I'd recommend booting into deadlock and running the local-deadlock-api-ingest for a bit so that it can backfill your old match data to the local API but its not necessary just may take a little longer for your new matches to be ready during your first session.
Otherwise to stop the containers run `docker compose -f deadlock-api-compose.yml stop`

---

## Per-Session Instructions

These steps are done each time you want to play a session of Deadlockipelago.

### Step 1 - Open a terminal

Open a terminal thats navigated to where the compose.yml is.

### Step 2 - Start the Containers

`docker compose -f deadlock-api-compose.yml start` This just starts the container. 

**Make sure all containers are started up properly before next step**.

### Step 3 - Run the local-deadlock-api-ingest & deadlock-api-ingest

Open 2 more Terminal sessions. Run the local-ingest and the standard ingest in those terminals.

*Why run in terminal?* Technically you don't need to its just if you do you can see if any errors happen in the logs as well you can just close the terminals to stop them from ingesting otherwise you have to open task manager to kill them (on Windows idk about Linux).

#### Windows

Navigate in terminal to where the exes are located.

> This requires the Terminal software which is automatically included and the default CLI software on Windows 11. For Windows 10 you need to install terminal from the [Microsoft Store](https://apps.microsoft.com/detail/9n0dx20hk701?hl=en-US&gl=US). These commands do not work on Win 10's native powershell and command prompt CLIs (for some reason).

run `./local-deadlock-api-ingest-windows-X.X.X.exe` in the terminal. (X.X.X will be version number)
run `./deadlock-api-ingest-windows-latest.exe` in the other terminal. (Standard doesn't have version number in the exe's name)

#### Linux

-- TODO: Put real instructions here.

I don't know how Linux desktop environment is I've only used CLI for servers just run both.

### Step 4 - Stopping

When you stop the session just run `docker compose -f deadlock-api-compose.yml stop` in the terminal thats in the directory of the compose.yml that and close all 3 terminal inlcuding the 2 running the local and standard deadlock-api-ingest.

---

## Delete/Uninstall Instructions

How to delete the containers.

## Step 1 - Navigate in Terminal

Navigate to the compose.yml again

### Step 2 - Delete the containers

run `docker compose -f deadlock-api-compose.yml down` This will delete the containers as well as all data inside them.

---

## FAQ

### What does it do?

This runs a local version of deadlock-api on your device using docker.

### What is Docker?

It runs Virtual Machine like environements (not exactly simplified) that automatically install and run their coresponding software in this case a 3 databases and the deadlock-api site.

### Is this safe?

Yes, it runs the official docker images for Redis, Clickhouse, Postgres, and Deadlock-API. [You can check the compose yourself here](https://github.com/ArchipelagoBrad/deadlockipelago/blob/main/local-deadlock-api/deadlock-api-compose.yml).
As for the the local version of deadlock-api-ingest its [code is available here](https://github.com/GreenestJ/local-deadlock-api-ingest). The only changes between this project and the official release is it uploads the match salts to your local version of deadlock-api instead of the regular public one.
