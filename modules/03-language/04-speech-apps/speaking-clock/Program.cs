using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Configuration;

static void PrintBanner(string title)
{
    Console.WriteLine();
    Console.WriteLine(new string('=', 80));
    Console.WriteLine(title);
    Console.WriteLine(new string('=', 80));
}

var config = new ConfigurationBuilder()
    .AddJsonFile("appsettings.json", optional: false)
    .AddEnvironmentVariables()
    .Build();

var endpoint = config["AI_SERVICE_ENDPOINT"] ?? string.Empty;
var apiKey = config["AI_SERVICE_KEY"] ?? string.Empty;
var sttDeployment = config["TRANSCRIBE_MODEL_DEPLOYMENT"] ?? "gpt-4o-transcribe";
var ttsDeployment = config["SPEAK_MODEL_DEPLOYMENT"] ?? "tts";

if (string.IsNullOrWhiteSpace(endpoint) || !endpoint.Contains("openai.azure.com"))
{
    Console.WriteLine("Error: AI_SERVICE_ENDPOINT must be your Azure OpenAI endpoint (…openai.azure.com).");
    Console.WriteLine($"Current endpoint: {endpoint}");
    return;
}
if (string.IsNullOrWhiteSpace(apiKey))
{
    Console.WriteLine("Error: AI_SERVICE_KEY is not set. Set KEY1/KEY2 from your Azure OpenAI resource.");
    return;
}

var http = new HttpClient();
http.BaseAddress = new Uri(endpoint);
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
var apiVersion = "2024-10-01-preview";

PrintBanner("Speaking Clock - Azure AI Foundry (.NET)");

// Recognize command from time.wav (same file name as Python sample)
var root = AppContext.BaseDirectory;
var audioPath = Path.Combine(root, "time.wav");
if (!File.Exists(audioPath))
{
    Console.WriteLine($"Error: Audio file not found at {audioPath}");
    return;
}

Console.WriteLine("Transcribing audio...");
string command = string.Empty;
try
{
    using var content = new MultipartFormDataContent();
    await using var audioStream = File.OpenRead(audioPath);
    var audioContent = new StreamContent(audioStream);
    audioContent.Headers.ContentType = new MediaTypeHeaderValue("audio/wav");
    content.Add(audioContent, "file", "time.wav");
    content.Add(new StringContent("en"), "language");

    var sttUrl = $"/openai/deployments/{sttDeployment}/audio/transcriptions?api-version={apiVersion}";
    var resp = await http.PostAsync(sttUrl, content);
    resp.EnsureSuccessStatusCode();
    var json = await resp.Content.ReadAsStringAsync();
    using var doc = JsonDocument.Parse(json);
    command = doc.RootElement.GetProperty("text").GetString() ?? string.Empty;
    Console.WriteLine($"Recognized: {command}");
}
catch (Exception ex)
{
    Console.WriteLine($"Transcription error: {ex.Message}");
    Console.WriteLine("Hint: Ensure the deployment name exists under your OpenAI resource and matches TRANSCRIBE_MODEL_DEPLOYMENT.");
    return;
}

if (!string.Equals(command.Trim(), "what time is it?", StringComparison.OrdinalIgnoreCase))
{
    Console.WriteLine("\nCommand not recognized. Expected: 'What time is it?'");
    return;
}

// Synthesize response
var now = DateTime.Now;
var responseText = $"The time is {now.Hour}:{now.Minute:00}";
var outputPath = Path.Combine(root, "output.wav");
Console.WriteLine("\nSynthesizing speech...");
try
{
    var body = new
    {
        input = responseText,
        voice = "alloy"
    };
    var ttsUrl = $"/openai/deployments/{ttsDeployment}/audio/speech?api-version={apiVersion}";
    var req = new HttpRequestMessage(HttpMethod.Post, ttsUrl)
    {
        Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json")
    };
    var ttsResp = await http.SendAsync(req);
    ttsResp.EnsureSuccessStatusCode();
    var audioBytes = await ttsResp.Content.ReadAsByteArrayAsync();
    await File.WriteAllBytesAsync(outputPath, audioBytes);
    Console.WriteLine($"Spoken output saved to {outputPath}");
}
catch (Exception ex)
{
    Console.WriteLine($"Synthesis error: {ex.Message}");
    Console.WriteLine($"Note: Ensure '{ttsDeployment}' deployment exists on the SAME Azure OpenAI resource as endpoint.");
}

Console.WriteLine($"Text response: {responseText}");
