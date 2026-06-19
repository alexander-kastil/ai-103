using System;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Azure.Identity;
using Microsoft.Extensions.Configuration;

class Program
{
    static async Task Main()
    {
        try
        {
            var config = new ConfigurationBuilder()
                .SetBasePath(AppContext.BaseDirectory)
                .AddJsonFile("appsettings.json", optional: false, reloadOnChange: false)
                .Build();

            var projectEndpoint = config["ProjectEndpoint"] ?? string.Empty;
            var modelDeployment = config["ModelDeployment"] ?? string.Empty;
            var apiVersion = config["ApiVersion"] ?? string.Empty;

            Console.WriteLine("Configuration:");
            Console.WriteLine($"  Endpoint: {projectEndpoint}");
            Console.WriteLine($"  Model: {modelDeployment}");
            Console.WriteLine($"  API Version: {apiVersion}\n");

            var systemMessage = "You are an AI assistant for a produce supplier company.";
            var prompt = "Who was calling, and what did they want?";

            Console.WriteLine("Getting a response ...\n");
            Console.WriteLine($"Prompt: {prompt}\n");

            // Resolve audio file path (linked into output as avocados.mp3)
            var audioPath = Path.Combine(AppContext.BaseDirectory, "avocados.mp3");
            if (!File.Exists(audioPath))
            {
                Console.WriteLine($"Error: Audio file not found at {audioPath}");
                return;
            }

            Console.WriteLine("Loading local audio file: avocados.mp3");
            var audioBytes = await File.ReadAllBytesAsync(audioPath);
            var audioBase64 = Convert.ToBase64String(audioBytes);
            Console.WriteLine($"Audio data encoded: {audioBase64.Length} chars\n");

            // Acquire bearer token using DefaultAzureCredential for scope https://ai.azure.com/.default
            var credential = new DefaultAzureCredential();
            var token = await credential.GetTokenAsync(new Azure.Core.TokenRequestContext(new[] { "https://ai.azure.com/.default" }));

            // Construct models endpoint from project endpoint
            // project endpoint format: https://.../api/projects/<name>
            var apiIndex = projectEndpoint.IndexOf("/api/", StringComparison.OrdinalIgnoreCase);
            if (apiIndex < 0)
            {
                Console.WriteLine("Error: PROJECT_ENDPOINT does not contain /api/ segment");
                return;
            }
            var resourceUrl = projectEndpoint.Substring(0, apiIndex);
            var apiUrl = $"{resourceUrl}/models/chat/completions?api-version={apiVersion}";

            var payload = new
            {
                model = modelDeployment,
                messages = new object[]
                {
                    new { role = "system", content = systemMessage },
                    new
                    {
                        role = "user",
                        content = new object[]
                        {
                            new { type = "text", text = prompt },
                            new { type = "input_audio", input_audio = new { data = audioBase64, format = "mp3" } }
                        }
                    }
                }
            };

            var json = JsonSerializer.Serialize(payload);
            using var http = new HttpClient();
            using var req = new HttpRequestMessage(HttpMethod.Post, apiUrl)
            {
                Content = new StringContent(json, Encoding.UTF8, "application/json")
            };
            req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);

            var resp = await http.SendAsync(req);
            var body = await resp.Content.ReadAsStringAsync();

            if (resp.IsSuccessStatusCode)
            {
                using var doc = JsonDocument.Parse(body);
                var choices = doc.RootElement.GetProperty("choices");
                var message = choices[0].GetProperty("message").GetProperty("content").GetString();
                Console.WriteLine("Response:");
                Console.WriteLine(message);
            }
            else
            {
                Console.WriteLine($"Error ({(int)resp.StatusCode}): {body}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
        }
    }
}
