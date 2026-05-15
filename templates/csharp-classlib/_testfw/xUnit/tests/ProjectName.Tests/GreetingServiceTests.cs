using ProjectName.Services;
using Xunit;

namespace ProjectName.Tests;

public class GreetingServiceTests
{
    [Fact]
    public void GetGreeting_ReturnsNonEmptyMessage()
    {
        IGreetingService sut = new GreetingService();

        var result = sut.GetGreeting();

        Assert.False(string.IsNullOrEmpty(result));
    }
}
