## Steps to Start the Project

1. **Clone the Repository**:

   ```bash
   git clone <repository-url> banking-mcps
   ```

2. **Navigate to the Project Directory**:

   ```bash
   cd banking-mcps
   ```

3. **Create a `.env` File**:
   Copy the example environment file and add your env variable key:

   ```bash
   cp env.example .env
   ```

4. **Build and Start the Docker Containers**:
   Use Docker Compose to build and start the containers:

   ```bash
   docker compose up --build
   ```

5. **Run MCP Inspector**:
   MCP Inspector can be used to test and inspect the MCP server. To test the running mcp server using MCP Inspector, follow these steps:

- Start MCP Inspector:

  ```bash
  npx @modelcontextprotocol/inspector http://localhost:8000/mcp
  ```

- Test the available tools and endpoints directly from the MCP Inspector interface.

- In the Authentication section, Add the custom auth as following
  - header name: mcp-authentication
  - header value: <MCP_AUTH_TOKEN>

## Notes

- The `docker-compose.yml` file is pre-configured to expose the API on port `8000`. If you need to change the port, update the `docker-compose.yml` file accordingly.
