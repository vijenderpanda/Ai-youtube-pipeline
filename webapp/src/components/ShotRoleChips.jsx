import { shotRolesOf, shotCoverage } from '../assetCatalog'

/**
 * ShotRoleChips — the pieces the EP15 post-mortem needed VISIBLE.
 *
 * The library showed one cover thumbnail per host outfit, so there was no way
 * to see that outfit_12 lacks the frames a Short needs — and nothing stopped
 * locking that unrenderable cast. This surfaces both, from the SAME meta.heygen
 * signal the build reads:
 *
 *   • a role chip listing what the outfit provides — `pip · wide` (green, a
 *     short host) vs `closeup · rest` (amber, long-form only);
 *   • a FIT badge driven by shotCoverage() — the one source of truth the
 *     composer's Phase-3 lock-block uses — reading `✓ fits this short` or
 *     `⚠ long-form host — no pip/wide`.
 *
 * Renders nothing for a non-host slot (no shot roles) or a host row that has no
 * recorded roles yet (older rows predate the field — absence is unknown, not
 * "incapable", so we assert nothing rather than a false warning).
 *
 * @param version   a factory_asset_versions row (needs asset_type + meta.heygen)
 * @param required  shot roles this format needs (default: Short pip+wide)
 * @param showFit   also render the ✓/⚠ fit badge (off when there is no format
 *                  to judge against, e.g. a long-form template)
 */
export default function ShotRoleChips({ version, required, showFit = true, className = '' }) {
  const roles = shotRolesOf(version)
  if (roles.length === 0) return null
  const cov = shotCoverage(version, required)
  const rolesTitle =
    'Shot roles this host provides: ' +
    roles.join(', ') +
    '. A short needs pip + wide' +
    (cov.fits ? '.' : ' — this one can’t render a short.')
  const fitTitle = cov.fits
    ? 'Has pip + wide — can render this short'
    : cov.warn || 'Missing the pip/wide frames a short needs'
  return (
    <span className={'shot-roles' + (className ? ' ' + className : '')}>
      <span
        className={'chip shot-role-chip' + (cov.fits ? ' shot-fit' : ' shot-unfit')}
        title={rolesTitle}
      >
        {roles.join(' · ')}
      </span>
      {showFit && (
        <span
          className={'chip shot-fit-badge' + (cov.fits ? ' shot-fit' : ' shot-unfit')}
          title={fitTitle}
        >
          {cov.fits ? '✓ fits this short' : '⚠ long-form host — no pip/wide'}
        </span>
      )}
    </span>
  )
}
