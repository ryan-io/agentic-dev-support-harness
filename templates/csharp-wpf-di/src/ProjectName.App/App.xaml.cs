using System.Windows;
using ProjectName.Core.Services;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace ProjectName.App;

/// <summary>
/// Composition root. All services resolve through the generic host's DI container.
/// </summary>
public partial class App : Application
{
    private readonly IHost _host;

    public App()
    {
        _host = Host.CreateDefaultBuilder()
            .ConfigureServices(ConfigureServices)
            .Build();
    }

    private static void ConfigureServices(HostBuilderContext context, IServiceCollection services)
    {
        services.AddSingleton<IGreetingService, GreetingService>();

        services.AddSingleton<ViewModels.MainViewModel>();
        services.AddSingleton<MainWindow>();
    }

    protected override async void OnStartup(StartupEventArgs e)
    {
        await _host.StartAsync();
        _host.Services.GetRequiredService<MainWindow>().Show();
        base.OnStartup(e);
    }

    protected override async void OnExit(ExitEventArgs e)
    {
        await _host.StopAsync();
        _host.Dispose();
        base.OnExit(e);
    }
}
