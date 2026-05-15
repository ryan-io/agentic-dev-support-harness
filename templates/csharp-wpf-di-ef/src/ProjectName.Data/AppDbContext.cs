using Microsoft.EntityFrameworkCore;

namespace ProjectName.Data;

/// <summary>
/// EF Core context. Registered via AddDbContext in the App composition root.
/// SQLite is the scaffold default; swap the provider in App.ConfigureServices.
/// </summary>
public sealed class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
    {
    }

    // Add DbSet<TEntity> properties as the domain model grows.
}
