using ProjectName.Core.Services;
using NUnit.Framework;

namespace ProjectName.Tests;

[TestFixture]
public class GreetingServiceTests
{
    [Test]
    public void GetGreeting_ReturnsNonEmptyMessage()
    {
        IGreetingService sut = new GreetingService();

        var result = sut.GetGreeting();

        Assert.That(result, Is.Not.Null.And.Not.Empty);
    }
}
