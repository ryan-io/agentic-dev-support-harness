using System.ComponentModel;
using System.Runtime.CompilerServices;
using ProjectName.Core.Services;

namespace ProjectName.App.ViewModels;

/// <summary>
/// View model for the main window. Business logic lives in Core services,
/// never in the view or view model (see code-standards: separation of concerns).
/// </summary>
public sealed class MainViewModel : INotifyPropertyChanged
{
    private string _greeting;

    public MainViewModel(IGreetingService greetingService)
    {
        _greeting = greetingService.GetGreeting();
    }

    public string Greeting
    {
        get => _greeting;
        set
        {
            if (_greeting == value) return;
            _greeting = value;
            OnPropertyChanged();
        }
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
}
