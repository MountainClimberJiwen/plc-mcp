using System;
using System.Xml.Linq;
using Serilog;

class Program
{
    static void Main(string[] args)
    {
        // Create an instance of the converter
        var converter = new SclToXmlConverter();

        // Example SCL code
        string sclCode = "m3 := m1 - m2;";

        // Convert the SCL code to XML
        XDocument xmlDoc = converter.ConvertSclToXml(sclCode, "Block_4", "2");

        // Save the XML to a file
        xmlDoc.Save("output.xml");

        Console.WriteLine("XML file has been generated successfully!");
        Console.WriteLine("Press any key to exit...");
        Console.ReadKey();
    }
}

var builder = WebApplication.CreateBuilder(args);

// Configure Serilog
Log.Logger = new LoggerConfiguration()
    .WriteTo.Console()
    .WriteTo.File("logs/myapp.txt", rollingInterval: RollingInterval.Day)
    .CreateLogger();

try
{
    Log.Information("Starting web application");

    builder.Host.UseSerilog(); // Use Serilog for logging

    var app = builder.Build();

    app.Run();
}
catch (Exception ex)
{
    Log.Fatal(ex, "Application terminated unexpectedly");
}
finally
{
    Log.CloseAndFlush();
} 