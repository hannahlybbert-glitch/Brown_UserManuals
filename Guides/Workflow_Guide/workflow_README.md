<!-- # Author: Hannah Lybbert
# Created: 06/08/2026
# Updated: 06/08/2026
# Purpose: Explaining the workflow using GitHub and Claude Code -->


# GitHub & Claude Code Workflow

## Overview
Claude Code is an incredibly powerful tool that will help you in your work. It is important to learn how to use it and stay organized while using it. This is a guide to using Claude Code in conjunction with Github and Git Issues.

## Git Issues & Communication
Git Issues are important for two reasons: (1) they are the primary source of documentation in a project and (2) they are your main mode of communication with Matt regarding code, analysis, data structure etc.
1. **Documentation**
   - **One topic per issue**: Git Issues are where we document everything done throughout a project, so it is important to follow the "**one topic per issue**" rule to maintain organization. Open a new issue whenever there is a new topic, analysis decision or question that needs to be discussed. If a conversation within an issue is diverging to a new topic, open a new issue and shift the coversation there. Sometimes it makes sense to split a larger task into multiple Git Issues; use best judgement here.
   - **Issue names**: Issue titles should be **specific** and **concise** in describing the topic of the issue so it is easy to navigate to past conversations (ex. "Incorporate mobile data into analysis pipeline", or "Building aggregation script (state, week, website level)")
   - The first thing you should do after opening a new issue is write a sentence or two comment about the purpose of the issue ("The purpose of this issue is...")
   - Some issues will be just a couple of comments long, that is okay. Some will be dozens long, that is also okay as long as the topic is consistent. 
   - **Add comments to relevant issues while you work.** This doesn't need to be excessive, just if there is a decision you make or a result produced that is worth docummenting or if you have a question you have that needs to be resolved.
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
- If you are doing a **multi-step coding** process where one script depends on the output of a previous script, **label the scripts numerically**. For example, see [`code/Aggregation/`](https://github.com/hannahlybbert-glitch/Brown_UserManuals/tree/main/AgeVerification/code/Aggregation) where we have scripts 1_ through 5_ for the aggregation pipeline. Script `4_aggregate_machine_month.py` uses as input the intermediate session files created in `2_create_intermediate_sessions.py`, so script 2 must have run prior to running script 4. 


## Working with Claude Code
Claude code is a crazy powerful productivity enhancer. It can also lead to a lot of sloppiness and errors if you are not careful. Matt likes to say "Claude giveth bugs, but it also taketh away bugs", you just have to be able to identify the bugs!

**What Claude is good at**
- Writing code
- Finding code or analysis steps that got lost. (ex. "In which script did we winsorize the data at the session level?")
- Explaining data hierarchy and how scripts are related
- Explaining what a script does (ex. "What does check_machine_person_coverage.py do and in which GitHub Issues is it referenced?")
- Suggesting solutions to problems
- Misinterpretting what you want it to do - you have to be clear and ask it to ask you questions.
- Writing Git Issue comments, sometimes. It is good at adding data into markdown tables and summarizing short sessions or general ideas.
    - At the end of a session, you can ask Claude "Can you add a comment to issue #5 explaining concisely what we covered in this session {be more specific here than I am}?" The more precise your instructions the better a comment it will write. If you don't give good instructions the comment will be unnecessarily long.


**What Claude is not good at**
- Understanding with one setence what you want.
- Writing git issue comments. See General Tips #3.2
- Cleaning up stale comments from previous edits. 
    - Claude does a good job of adding in comments to its code, but then when you have it make edits later, it will usually forget to update the comment and then get confused thinking that what is stated in the comments is what the code actually does!

**My Claude Code tips**
- **Small task**: something like asking it to remind you what a given script does or make a small change to a script (ex.adding a new variable to the output dataframe).
    - You can ask these directly in the terminal 
- **Medium task**: writting a full script, building a figure, re-organizing files, etc.
- **Large task**: a multi-script pipeline, re-working a previously coded analysis, brainstorming how to approach code you want to write, etc.
- **Framing a medium or large task for Claude**: 
    - For medium and larger task, I rarely type directly in the console and almost always draft out my prompt in a separate running Google Doc I have for the project and then copy and paste it into the terminal. 
    - For medium tasks, you can usually send the whole task at once if you are detailed enough.
    - For large tasks, send one task at a time (ex. building one script at a time instead of setting it loose to build 5 scripts at once)
    - Explain it to yourself in a google or word doc first before sending the task to Claude. Organize your thoughts so you can send Claude a coherent task instead of jumbled thoughts. Remember, Claude doesn't perform well with vague instructions!
    - Ask Claude to:
        - Clarify or ask you questions if it doesn't understand.
        - Provide a plan first of how it will execute the code. This is probably the number one way I catch Claude trying to slip a bug into the code.
        - Make a task list to track the steps it is doing/has done. 
- Create a `SCRIPT_BEST_PRACTICES.md` file which includes all of the coding practices you want Claude to follow. See an example [here](https://github.com/hannahlybbert-glitch/Brown_UserManuals/blob/main/AgeVerification/code/SCRIPT_BEST_PRACTICES.md). You can add to this script as new "best practices" come up.


## General tips
1. It might take you an extra minute or two to come up with a good name (for a commit, script, issue title, etc.) but do it or you will regret later when a name isn't intuitive. 
2. It might take you an extra 10-15 minutes (or longer!) to figure out the best way to organize something. Take that time instead of doing it blind. Organization is essential when you work with large data. I found it helpful to go to a whiteboard and draw out the relationships or the end goal and work back to the beginning. Use others as a sounding board!
3. **Claude code can make you sloppy. Don't let it.**
    1. I rarely set "auto-accept edits." I prefer to read the code it writes as it suggests edits to make sure I understand what the code does (and that it is doing the right thing!)
    2. I would suggest writing your own Git issue comments instead of having Claude do it. Writing helps you think. If Claude always writes the comments you will quickly have no idea what is going on in the project. 
    3. Make sure you take time to step back and look at the big picture frequently. It is easy to get wrapped up in the data and forget what is going on if you doing let yourself get up to speed with Claude.


## Workflow that works for me
Any time I sit down to work, this is the workflow I follow:
1. Open Github Desktop and click `Fetch origin`
2. Open windows powershell (or your local computer terminal) and cd into your project directory
    -  `cd "c:\Users\hlybbert\Documents\AgeVerification`
3. Type `claude` and click enter
4. Begin coding, following above tips on working with Claude
5. Every hour or so of work go back to Github Desktop and commit the changes you have made and click `Push origin`. 
6. At the end of your working session, push everything to git and add an issue comment of what was completed (if you finished mid-task, you do not need to add an issue comment).