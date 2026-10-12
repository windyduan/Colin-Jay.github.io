# Colin Jay Blog — GitHub Pages 部署说明

> 本仓库**只用于 Colin Jay 博客**；钻石 MAISON ÉCLAT 演示是另外一个独立项目，不放进此仓库。

## 本次改造

- 保留原 Hexo 生成的文章路径、文章内容、分类、标签、相册、关于页面等。
- 为博客首页 `index.html` 添加编辑风格、响应式样式 `css/blog-refresh.css`。
- 修正首页资源和导航链接的相对路径，使其能在项目站点子路径下加载。
- 添加 `.nojekyll`，表明已经是生成好的静态 HTML。
- 移除重复的 Jekyll GitHub Actions Pages 工作流，保留适用于纯静态 HTML 的 `.github/workflows/static.yml`。
- 规范根目录 `CNAME`：GitHub Pages 只应列一个主域名 `Colin-Jay.cn`；www 子域应在 DNS/域名配置处理。

## GitHub Pages 发布步骤

1. 将改造分支的 Pull Request 合并到 `master`。
2. 到仓库 `Settings → Pages`，将 **Source** 设置为 **GitHub Actions**。
3. 打开 `Actions → Deploy static content to Pages`，等待自动部署完成，或点击 **Run workflow** 手动执行。
4. 如果原自定义域名已正确配置且 DNS 生效，可访问 `https://colin-jay.cn/`。
5. 没有配置自定义域名时，项目站点默认模式预计位于 `https://windyduan.github.io/Colin-Jay.github.io/`；但仓库中保留的 CNAME 可能使 Pages 继续采用自定义域名。

## 路径与历史内容

这个仓库是旧的 Hexo *生成结果*，而非完整 Hexo 原始工程。首页已经兼容 GitHub Pages 仓库子路径，但历史文章中的绝对链接和资源仍按原自定义域名根路径构建。如果主要使用 `windyduan.github.io/Colin-Jay.github.io/` 的项目路径部署，历史页面可能需要再进行一次批量路径修复；如果使用 `Colin-Jay.cn` 根域名，则旧链接仍按原方式工作。

建议先确认 Actions 结果和 DNS 状态，再决定是否批量修改所有历史文章。改造是独立分支，不会在合并前影响现有线上主页。
