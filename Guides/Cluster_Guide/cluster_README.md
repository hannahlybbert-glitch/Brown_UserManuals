<!-- # Author: Hannah Lybbert
# Created: 06/08/2026
# Updated: 06/08/2026
# Purpose: Explaining the workflow using GitHub and Claude Code -->

# Midway RCC Cluster Guide

## Overview
Midway RCC is a computing cluster owned by UChicago which is where we keep all of our large data stored and where we run code that uses a lot of compute power. You will run most large jobs on Midway, but it does make sense to keep some smaller data files downloaded on your local computer so you can test smaller scripts without needing to synch everything to the cluster first.

## Opening a session on Midway
Get into your project directory:
1. Go to the [Midway home page](https://midway3-ondemand.rcc.uchicago.edu/pun/sys/dashboard)
2. Sign in using your CNET ID and password. This password will be used to access the Midway terminal and sync code from your local computer, so make sure you know it well!
3. Click the house icon that says "Home Directory". This will take you to your _own_ home directory which is _not_ where you will run jobs, you want to be in Matt's project directory.
4. Click "Change Directory", type /project/mattbrownecon/, and click "OK"
5. Click on your project folder and you should be able to see all the data, code, output, log files, etc. This is your main Midway-based project directory. 

Now that you are in the project directory, you are ready to open a session on Midway.
1. On the top of the page in the red banner, click the "Clusters" drop-down menu and select ">_ Midway3 cluster Terminal"
2. A new terminal tab will open and you will be prompted to enter your password. Note that you wont be able to see the characters of the password as you type but they are there (hence why you need to know your password well!)
    - You will be prompted to a two-factor login (I always do option 1 "Duo Push to my phone number" because its fastest! Just make sure you link your Duo account)
3. cd into your project directory
    - ex. `cd "/project/mattbrownecon/AgeVerification/"`
4. Activate your conda environment if you are using one
    - ex. `conda activate age-verification`
    - See notes 1 and 2 below for more info on conda environments
5. Run your job (see next section)


## Running Jobs
All of your code editing and building should take place on your local computer, but when it comes time to run the code on the cluster follow these steps.
1. **Create an .sh script** (see note #4 for how to create an .sh script)
2. **Sync local code to Midway.** (see note #5 for details)
```
# Mac:
rsync -avz --delete --no-g --chmod=D775,F775 code/ hlybbert@midway3.rcc.uchicago.edu:/project/mattbrownecon/AgeVerification/code/

# Windows:
wsl rsync -avz --delete --no-g --chmod=D775,F775 code/ hlybbert@midway3.rcc.uchicago.edu:/project/mattbrownecon/AgeVerification/code/
```
3. Open Midway3 cluster Terminal, cd into your project directory and activate your conda environment
4. Type `sbatch code/{file path where your .sh script lives}/{name}.sh` and click enter
    - ex. `sbatch code/Aggregation/master.sh`



## Helpful midway commands to know
Running an sbatch job: `sbatch code/analysis/make.sh`
Checking status of the job: `squeue -u $USER` 
Setting a watch on the job: `watch -n 10 squeue -u $USER`
    - Shows the status of the current job and updates every 10 seconds (can change 10 to how ever frequently you want it to update)
Cancel a job: `scancel {job_id}` (ex. scancel 5447892)




## Notes

1. Conda environments
Conda environements are where you can store packages that are used in your scripts. See our [`environment.yml`](https://github.com/mattbrownecon/AgeVerification/blob/main/environment.yml) file which you can replicate for your project.

2. Updating conda environment 
    * Open environment.yml file on your local computer and make needed edits, save file
    * Open a terminal on your local computer and cd in to your local project directory.
    * Sync using this command in your **local** terminal 
    * `rsync -avz --delete --no-g --chmod=D775,F775 environment.yml hlybbert@midway3.rcc.uchicago.edu:/project/mattbrownecon/AgeVerification/environment.yml`
    * remember to replace "hlybbert" with your CNET ID
    * Run the following commands from your **cluster** terminal:
```
    conda activate age-verification
    conda env update --file /project/mattbrownecon/AgeVerification/environment.yml --prune
```
3. Local computer and git directories should both match the structure of the cluster!

4. **Creating an .sh script**
- This is the only script you will run on the cluster.
    - Include a header which lists the settings for the job (see an example below)
    - What you need to change in this example:
        - `Author`, `Created`, `Updated`, and `Purpose` (as usual)
        - `Run from project root:` - this is just a note to whoever is running this script of how they need to run the job in the terminal
        - `job-name` - give the job a name
        - `output` - always keep the `logs/` just change "aggregation" to be the name of the log file
        - `error` - should match the output name
        - `time` - I would default to 2-4 hours for long jobs, 1 hour for short jobs. Claude is good at estimating time if you are unsure, although I always err on the side of caution and keep time limit longer because there is nothing worse than a long job timing out and having to start the run over!
        - `mem` - Default to 64GB or let Claude decide. If it crashes because out of memory, just increase and re-run.
            - Note that the more time and memory you request, the longer your job will sit in the queue before running, so try to be accurate.

```
#!/bin/bash
# Author: Name
# Created: date (updated: date)
# Purpose: 
# Run from project root: ./code/Aggregation/master.sh

#SBATCH --partition=caslake
#SBATCH --account=pi-mattbrownecon

#SBATCH --job-name=aggregation_pipeline
#SBATCH --output=logs/aggregation_%j.out
#SBATCH --error=logs/aggregation_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=64G
```

5. **Syncing local code to Midway.** 
    1. ctrl+S save your code on your local computer
    2. In a new terminal tab, cd into your local project directory
        - ex. `cd "C:\Users\hlybbert\Documents\AgeVerification\"`
    3. Run **exactly** this sync command in terminal:
        - Mac users:    
            `rsync -avz --delete --no-g --chmod=D775,F775 code/ hlybbert@midway3.rcc.uchicago.edu:/project/mattbrownecon/AgeVerification/code/`
        - Windows users:
            `wsl rsync -avz --delete --no-g --chmod=D775,F775 code/ hlybbert@midway3.rcc.uchicago.edu:/project/mattbrownecon/AgeVerification/code/`
    4. Enter your CNET ID password (you won't be able to see characters being typed but they are there) and do the two-factor authentication
    5. A bunch of `rsync: failed to set times on ...` will output and then you should see a list of the files that were added new to Midway (what you edited). This step usually looks like something failed or it didn't sync but the chances are that it did! Ask Claude if your edited code isn't showing up in the terminal.

    An example of the output I get when I sync:
```
(base) PS C:\Users\hlybbert\Documents\AgeVerification> wsl rsync -avz --delete --no-g --chmod=D775,F775 code/ hlybbert@midway3.rcc.uchicago.edu:/project/mattbrownecon/AgeVerification/code/
>>
(hlybbert@midway3.rcc.uchicago.edu) Password:
(hlybbert@midway3.rcc.uchicago.edu) Duo two-factor login for hlybbert

Enter a passcode or select one of the following options:

1. Duo Push to XXX-XXX-0017
2. Phone call to XXX-XXX-0017
3. SMS passcodes to XXX-XXX-0017

Passcode or option (1-3): 1
sending incremental file list
rsync: failed to set times on "/project/mattbrownecon/AgeVerification/code/.": Operation not permitted (1)
./
rsync: failed to set times on "/project/mattbrownecon/AgeVerification/code/ProcessComscore": Operation not permitted (1)
rsync: failed to set times on "/project/mattbrownecon/AgeVerification/code/ProcessComscore/config": Operation not permitted (1)
rsync: failed to set times on "/project/mattbrownecon/AgeVerification/code/ProcessComscore/config/__pycache__": Operation not permitted (1)
rsync: failed to set times on "/project/mattbrownecon/AgeVerification/code/ProcessComscore/data_structure_validation": Operation not permitted (1)
rsync: failed to set times on "/project/mattbrownecon/AgeVerification/code/__pycache__": Operation not permitted (1)
rsync: failed to set times on "/project/mattbrownecon/AgeVerification/code/descriptives": Operation not permitted (1)
ProcessComscore/
ProcessComscore/config/
ProcessComscore/config/__pycache__/
ProcessComscore/data_structure_validation/
__pycache__/
analysis/
analysis/create_decomp_plots2_pres.R
descriptives/

sent 10,285 bytes  received 1,129 bytes  507.29 bytes/sec
total size is 2,409,971  speedup is 211.14
rsync error: some files/attrs were not transferred (see previous errors) (code 23) at main.c(1338) [sender=3.2.7]
```