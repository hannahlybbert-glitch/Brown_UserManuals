<!-- # Author: Hannah Lybbert
# Created: 06/08/2026
# Updated: 06/08/2026
# Purpose: Explaining the workflow using GitHub and Claude Code -->


# GitHub & Claude Code Workflow

## Overview
Add overview notes here

## Git Issues & Communication
Git Issues are important for two reasons: (1) they are the primary source of documentation and (2) they are your main mode of communication with Matt regarding code, analysis, data structure etc.
1. **Documentation**
   - **One topic per issue**: Git Issues are where we document everything done throughout a project, so it is important to follow the "**one topic per issue**" rule to maintain organization. Open a new issue whenever there is a topic, analysis decision or question that needs to be discussed. If a conversation within an issue is diverging to a new topic, open a new issue and shift the coversation there.
   - **Issue names**: Issue titles should be **specific** and **concise** in describing the topic of the issue so it is easy to navigate to past conversations (ex. "Incorporate mobile data into analysis pipeline", or "Building aggregation script (state, week, website level)")
   - The first thing you should do after opening a new issue is write a sentence or two comment about the purpose of the issue ("The purpose of this issue is...")
   - Some issues will be just a couple of comments long, that is okay. Some will be dozens long, that is also okay as long as the topic is consistent. 
   - **Close issues** with a brief comment of what was accomplished in the issue when the topic of the issue has been resolved. It is good practice at the end of each week to check up on the issues to understand which issues are completed (close the issue) and which need to be revisted (keep issue open). 
2. **Communication**
   - **Tagging** to loop another project member in to a comment "@{githubid}" (ex. @mattbrownecon)
   - Make sure notifications are turned on for when you are tagged in a comment (you should receive an email when someone tags you in a comment)
   - Try to respond within 24 hours if you are tagged. When you see a comment you are tagged in, react to it to indicate you have seen it and are working on the task or responding to the comment.


## Commits & Fetching
- **Fetching**: Start each work session by "Fetching" the most recent version of the repository, this will ensure your local directory matches the GitHub directory, pulling any changes made by other project members.
- **Commit**: Every hour or so during a work session, it is good practice to "Commit" your changes to the GitHub repository, this ensures GitHub can track the changes made to the repository so we can return to older versions if needed.
   - **Commit summaries** should be brief and indicative of the changes made (ex. "Added criteria for missking/unknown markets" or "Fixing bug to run on cluster"). If you just created the script, something like "Create {script_name}.py" is okay.
   - **Tagging issues**: If the script relates to a Git Issue, you should tag the issue in the commit summary. For example, "Update event studies for combined analysis #32". In this case, Git Issue #32 would be realted to the desktop and mobile combined analysis. 


## Script/Code Organization
- At the top of each script, it is important to report the author, creation date, updated date, and purpose of the script in a comment.
```
        # Author: Hannah Lybbert
        # Created: 06/05/2026
        # Updated: 06/09/2026
        # Purpose: Create intermediate session-level files with week_of_sample and coarse_category
```
- **One task per script**: Each script should basically accomplish one task. For example in `code/analysis/`: `create_het_table.R` creates the heterogeneity _table_ but `create_het_main_figures.R` creates the main heterogeneity _figures_. Even though they are both related to heterogeneity plots, we separate them for cleanliness.
- If you are doing a **multi-step coding** process where one script depends on the output of a previous script, **label the scripts numerically**. For example, see `code/Aggregation/` where we have scripts 1_ through 5_ for the aggregation pipeline. Script `4_aggregate_machine_month.py` uses as input the intermediate session files created in `2_create_intermediate_sessions.py`, so script 2 must have run prior to running script 4. 
- 


## Working with Claude Code
Claude code is a crazy powerful productivity enhancer. It can also lead to a lot of sloppiness and errors if you are not careful. Matt likes to say "Claude giveth bugs, but it also taketh away bugs", you just have to be able to identify the bugs!

**What Claude is good at**
- Writing code
- Misinterpretting what you want it to do - you have to be clear and ask it to ask you questions.
- Finding code or analysis steps that got lost. (ex. "In which script did we winsorize the data at the session level?")
- Explaining data hierarchy and how scripts are related
- Explaining what a script does (ex. "What does check_machine_person_coverage.py do and in which GitHub Issues is it referenced?")
- Suggesting solutions to problems

**What Claude is not good at**
- understanding with one setence what you want.

**My Claude Code tips**
- Small task: something like asking it to remind you what a given script does, make a small change to a script (ex.adding a new variable to the output dataframe) 
- Medium task
- **Framing a task for Claude**: If I am giving Claude a larger task, I rarely type directly in the console and almost always draft out my prompt in a separate running Google Doc I have for the project. 
- For large tasks, send one task at a timeSend one task at a time
- Explain it to yourself in a google or word doc first before sending the task to Claude
- Asking it to ask you question if it doesn't understand or to clarify. 
- Ask it to provide a plan first of how it will execute the code.
- Task list to track the steps it is doing/has done. 

- How to frame a task for Claude (what context to include)


## General tips
- it might take you an extra minute or two to come up with a good name (for a commit, script, issue title, etc.) but do it or you will regret later
- it might take you an extra 10-15 minutes to figure out the best way to organize something. Take that time instead of doing it sloppy. Organization is essential when you work with large data.
- organizing takes a few extra minutes but it is worth it.

## Claude code can make you sloppy. Don't let it. 
- at one point we had claude writing comments of what we had done in a session but I found that to quickly make me have no idea what was going on. So write your own comments unless its something tedious like building a markdown table that you don't want to do

- try to explain everything you want claude to do (including where to put certain files or output)
- can ask claude to ask you questions if it doesn't understand or explain back to you what you want it to do to make sure you understand.

## Workflow that works for me
1. Open github desktop and Fetch Origin
2. Open windows powershell or your computer terminal and cd into your project directory
3. type "claude" and enter
4. Begin coding (elaborate here on how to use claude)
5. Every hour or so of work go back to github desktop and commit the changes you have made
6. At the end of the session, push everything to git