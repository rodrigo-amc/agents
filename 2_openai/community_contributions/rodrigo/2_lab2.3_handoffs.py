import os
from agents import Agent, Runner, OpenAIChatCompletionsModel, function_tool
import asyncio
from dotenv import load_dotenv
from openai.types.responses import ResponseTextDeltaEvent
from openai import AsyncOpenAI
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import Dict
from zroddeUtils import llmModels


#region HANDOFFS
# In this case there will be a handoff, an agent will delegate a task to another agent.
# The 'emailer_agent' will have tools to perform an email subject, convert the email
# body to HTML and send (write in a file) the email.
# 
# The 'sales_manager' will 'have' the handoff to the 'emailer_agent'. Also
# will have tools (agents) that will generate the email body.
#endregion


load_dotenv(override=True)
sendgridApiKey = os.getenv("SENDGRID_API_KEY")
openRouterApiKey = os.getenv("OPENROUTER_API_KEY")

# These are three differrent prompts. Each one for a different agent
instructions1 = "You are a sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 \
compliance and preparing for audits, powered by AI. \
You write professional, serious cold emails.\
You just write the email body, without any extra content"

instructions2 = "You are a humorous, engaging sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 compliance and \
preparing for audits, powered by AI. \
You write witty, engaging cold emails that are likely to get a response.\
You just write the email body, without any extra content"

instructions3 = "You are a busy sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 \
compliance and preparing for audits, powered by AI. \
You write concise, to the point cold emails.\
You just write the email body, without any extra content"


# region this is nescessary for work with OpenAI SDK using OpenRouter API
# Create an AsyncOpenAI client with OpenRouter API credentials
asyncOpenAIClient = AsyncOpenAI(
    api_key = openRouterApiKey,
    base_url = "https://openrouter.ai/api/v1"
)

# Create a custom model using OpenRouter
openRouterModel = OpenAIChatCompletionsModel(
    # here you can choose the model that you prefer from OpenRouter
    model = llmModels.Gemini_20_flash_001,
    openai_client = asyncOpenAIClient
)
# endregion

sales_agent1 = Agent(
    name = "Profesional Sales Agent",
    instructions = instructions1,
    model = openRouterModel
)

sales_agent2 = Agent(
    name = "Engaging Sales Agent",
    instructions = instructions2,
    model = openRouterModel
)

sales_agent3 = Agent(
    name = "Busy Sales Agent",
    instructions = instructions3,
    model = openRouterModel
)


# This tool will write the email body to a text file instead of sending it
# Get the absolute path of the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Set the path for the email.txt file in the same directory as the script
file_path = os.path.join(script_dir, "email.txt")

@function_tool
def writeEmailInFile(agentName:str, emailBody:str):
    """ Write the email in to a file. If the file doesn't exists, it will be created. If it exists, \
        the email will be appended to the file. Each email will be clearly separated."""
    # Open the file 'email.txt' in append mode ('a'), creating it if it doesn't exist
    with open(file_path, "a") as f:
        # Write the agent's name to the file
        f.write(f"Agent Name: {agentName}\n")
        # Write the agent's email to the file
        f.write(f"Email: {emailBody}\n")
        # Add a blank line to separate entries
        f.write("\n"+"*_"*50 + "\n")
    # Return a dictionary indicating success
    return {"status":"success"}


@function_tool
def reportAProblem(yourProblem:str)-> str:
    """ This tool is used to report a problem. You show the problem to the user and ask for a instruction to continue. \
        Once you report a problem, you will stop all your processes and wait for the user to give you a new instruction. """
    
    print("\n" + "="*40 + " PROBLEM REPORTED " + "="*40)
    print(yourProblem)
    print("="*100 + "\n")

    userInstruction = input("Please provide a new instruction to continue: ")

    return f"Problem reported: {yourProblem}. New instruction received: {userInstruction}"



#print(tool_send_email)

description = "Write a cold sales email"

tool1 = sales_agent1.as_tool(tool_name = "sales_agent1_tool", tool_description = description)
tool2 = sales_agent2.as_tool(tool_name = "sales_agent2_tool", tool_description = description)
tool3 = sales_agent3.as_tool(tool_name = "sales_agent3_tool", tool_description = description)

salesManagers_tools = [tool1, tool2, tool3, reportAProblem]


# region HANDOFF
# Here is the code related to handoff agent, the emailer_agent.
# instructions for agents that will generate the email subject, and convert the email body to HTML.
subject_instructions = "You can write a subject for a cold sales email. \
You are given a message and you need to write a subject for an email that is likely to get a response."

html_instructions = "You convert a text email body to an HTML email body. \
You are given a text email body which might have some markdown \
and you need to convert it to an HTML email body with simple, clear, compelling layout and design.\
Use HTML tags to format the email body and add basic styling."

# The agents that will generate the email subject, and convert the email body to HTML.
subject_writer = Agent(name="Email Subject Writer", instructions=subject_instructions, model=openRouterModel)
subject_writer_tool = subject_writer.as_tool(tool_name="subject_writer", tool_description="Write a subject for a cold sales email")

html_converter = Agent(name="HTML email body converter", instructions=html_instructions, model=openRouterModel)
html_converter_tool = html_converter.as_tool(tool_name="html_converter", tool_description="Convert a text email body to an HTML email body")

# The tools for the emailer_agent
emailer_agent_tools = [subject_writer_tool, html_converter_tool, writeEmailInFile, reportAProblem]

# emailer_agent instructions
emailerAgent_instructions ="You are an email formatter and sender. You receive the body of an email to be sent. \
You first use the subject_writer tool to write a subject for the email, then use the html_converter tool to convert the body to HTML. \
Finally, you use the writeEmailInFile tool to send the email with the subject and HTML body."

emailer_agent = Agent(name="Emailer Agent",
                      instructions = emailerAgent_instructions,
                      tools = emailer_agent_tools,
                      model = openRouterModel,
                      handoff_description = "Convert an email to HTML and send it")

# You must pay atention to the handoff_description, it is used to describe the handoff to the user.
# If you don't provide a handoff_description, the agent will not be able to perform the handoff.

#endregion HANDOFF


## Sales Manager Agent
salesManagerInstructions = "Your are a sales manager working for ComplAI. You use the tools given to you to\
    generate cold sales emails. You never generate sales emails yourself; you always use the tools.\
    You try all 3 sales_agent tools once before choosing the best one.\
    You can use the tools multiple times if you're not satisfied with the results from the first try. \
    You select the single best email using your own judgement of which email will be most effective. \
    After picking the email, you handoff to the Email Manager agent to format and send the email."

sales_manager = Agent(
    name = "Sales Manager",
    instructions = salesManagerInstructions,
    model = openRouterModel,
    tools = salesManagers_tools,
    handoffs = [emailer_agent],
    turns = 30)


message = "Send a cold sales email addressed to 'Dear CEO'"



async def main():
    result = await Runner.run(sales_manager, message)


if __name__ == "__main__":
    asyncio.run(main())