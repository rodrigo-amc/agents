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


#region THIS EXAMPLE DID NOT WORK FOR ME 
# 
# - (to test it, you have to replace 'yourEmail' with your email address)
#
#
# Although it runs without errors, SendGrid does not detect any activity and, of course, I do not receive
# any email in my inbox. Not even in the spam folder.
# 
# Intead of send an email, I will write the email body in a text file.
#
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


""" @function_tool
def tool_send_email(body:str):
    """" Send out an email with the given body to all sales prospects """"
    sg = sendgrid.SendGridAPIClient(api_key = sendgridApiKey)
    from_email = Email("sender@gmail.com")
    to_email = To("yourEmail@gmail.com")
    content = Content("text/plain", body)
    mail = Mail(from_email, to_email, "Sales Email", content).get()
    response =  sg.client.mail.send.post(request_body=mail)
    return {"status":"success"} """
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

tools = [tool1, tool2, tool3, writeEmailInFile, reportAProblem]


## And now it's time for our Sales Manager - our planning agent
# We're giving an agent the ability to choose what to run and when.
# It's not like just writing Python code to run ir programmatically.
# We're letting the agent decide.
salesManagerInstructions = "Your are a sales manager working for ComplAI. You use the tools given to you to\
    generate cold sales emails. You never generate sales emails yourself; you always use the tools.\
    You try all 3 sales_agent tools once before choosing the best one.\
    You pick the single best email and use the 'writeEmailInFile' tool to write the best email \
    (and only the best email). to the user"
 

sales_manager = Agent(
    name = "Sales Manager",
    instructions = salesManagerInstructions,
    model = openRouterModel,
    tools = tools)


message = "Send a cold sales email addressed to 'Dear CEO'"



async def main():
    result = await Runner.run(sales_manager, message)


if __name__ == "__main__":
    asyncio.run(main())