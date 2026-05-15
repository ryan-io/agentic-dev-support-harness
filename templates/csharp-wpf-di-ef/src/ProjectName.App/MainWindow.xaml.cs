using System.Windows;
using ProjectName.App.ViewModels;

namespace ProjectName.App;

public partial class MainWindow : Window
{
    public MainWindow(MainViewModel viewModel)
    {
        InitializeComponent();
        DataContext = viewModel;
    }
}
