using ProjectName.Services;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace ProjectName.Tests;

[TestClass]
public class GreetingServiceTests
{
    [TestMethod]
    public void GetGreeting_ReturnsNonEmptyMessage()
    {
        IGreetingService sut = new GreetingService();

        var result = sut.GetGreeting();

        Assert.IsFalse(string.IsNullOrEmpty(result));
    }
}
