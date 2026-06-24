using Microsoft.Extensions.Logging;

public class ExampleClass
{
    private readonly ILogger<ExampleClass> _logger;

    public ExampleClass(ILogger<ExampleClass> logger)
    {
        _logger = logger;
    }

    public void DoSomething()
    {
        try
        {
            _logger.LogInformation("Starting to do something");
            
            // Your business logic here
            
            _logger.LogInformation("Successfully completed the operation");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "An error occurred while doing something");
            throw;
        }
    }
} 