import os
import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from zroddeUtils import llmModels


# I work in this Python file because I can't use Notebooks as the video shows.
# When I try to use notebooks with this exercises, I get an error, because I'm
# using the OpenRouter API key but, in this case, it doesn't work with notebooks.
async def main():
    # Load environment variables from .env file
    load_dotenv(override=True)
    
    
    # Create an AsyncOpenAI client with OpenRouter API credentials
    asyncOpenAIClient = AsyncOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )
    
    # Create a custom model OpenRouter model
    model = OpenAIChatCompletionsModel(
        model=llmModels.free_mistral_Small_31_24B,
        openai_client=asyncOpenAIClient
    )
    
    # Create an agent with comedian personality
    agent = Agent(
        name="Jokester",
        instructions="You are a comedian. Tell short, clever jokes.",
        model=model
    )
    
    # Run the agent and ask for a programmer joke
    result = await Runner.run(agent, "Tell me a joke about programmers")
    print(result.final_output)

# Execute the async main function
asyncio.run(main())