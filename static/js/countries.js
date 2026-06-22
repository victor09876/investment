// Country list with dial codes and states for the state dropdown
const COUNTRIES = [
  {name:"United States", code:"US", dial:"+1"},
  {name:"United Kingdom", code:"GB", dial:"+44"},
  {name:"Canada", code:"CA", dial:"+1"},
  {name:"Australia", code:"AU", dial:"+61"},
  {name:"Germany", code:"DE", dial:"+49"},
  {name:"France", code:"FR", dial:"+33"},
  {name:"Italy", code:"IT", dial:"+39"},
  {name:"Spain", code:"ES", dial:"+34"},
  {name:"Netherlands", code:"NL", dial:"+31"},
  {name:"Switzerland", code:"CH", dial:"+41"},
  {name:"Sweden", code:"SE", dial:"+46"},
  {name:"Norway", code:"NO", dial:"+47"},
  {name:"Ireland", code:"IE", dial:"+353"},
  {name:"Portugal", code:"PT", dial:"+351"},
  {name:"Poland", code:"PL", dial:"+48"},
  {name:"Nigeria", code:"NG", dial:"+234"},
  {name:"Ghana", code:"GH", dial:"+233"},
  {name:"Kenya", code:"KE", dial:"+254"},
  {name:"South Africa", code:"ZA", dial:"+27"},
  {name:"Egypt", code:"EG", dial:"+20"},
  {name:"Morocco", code:"MA", dial:"+212"},
  {name:"India", code:"IN", dial:"+91"},
  {name:"Pakistan", code:"PK", dial:"+92"},
  {name:"Bangladesh", code:"BD", dial:"+880"},
  {name:"China", code:"CN", dial:"+86"},
  {name:"Japan", code:"JP", dial:"+81"},
  {name:"South Korea", code:"KR", dial:"+82"},
  {name:"Singapore", code:"SG", dial:"+65"},
  {name:"Malaysia", code:"MY", dial:"+60"},
  {name:"Indonesia", code:"ID", dial:"+62"},
  {name:"Philippines", code:"PH", dial:"+63"},
  {name:"Vietnam", code:"VN", dial:"+84"},
  {name:"Thailand", code:"TH", dial:"+66"},
  {name:"United Arab Emirates", code:"AE", dial:"+971"},
  {name:"Saudi Arabia", code:"SA", dial:"+966"},
  {name:"Turkey", code:"TR", dial:"+90"},
  {name:"Israel", code:"IL", dial:"+972"},
  {name:"Brazil", code:"BR", dial:"+55"},
  {name:"Mexico", code:"MX", dial:"+52"},
  {name:"Argentina", code:"AR", dial:"+54"},
  {name:"Chile", code:"CL", dial:"+56"},
  {name:"Colombia", code:"CO", dial:"+57"},
  {name:"Peru", code:"PE", dial:"+51"},
  {name:"Russia", code:"RU", dial:"+7"},
  {name:"Ukraine", code:"UA", dial:"+380"},
  {name:"New Zealand", code:"NZ", dial:"+64"},
  {name:"Other", code:"OT", dial:""},
];

const US_STATES = [
  "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware",
  "Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky",
  "Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota","Mississippi",
  "Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico",
  "New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania",
  "Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont",
  "Virginia","Washington","West Virginia","Wisconsin","Wyoming"
];

const NG_STATES = [
  "Abia","Adamawa","Akwa Ibom","Anambra","Bauchi","Bayelsa","Benue","Borno","Cross River",
  "Delta","Ebonyi","Edo","Ekiti","Enugu","Gombe","Imo","Jigawa","Kaduna","Kano","Katsina",
  "Kebbi","Kogi","Kwara","Lagos","Nasarawa","Niger","Ogun","Ondo","Osun","Oyo","Plateau",
  "Rivers","Sokoto","Taraba","Yobe","Zamfara","FCT - Abuja"
];

const CA_PROVINCES = [
  "Alberta","British Columbia","Manitoba","New Brunswick","Newfoundland and Labrador",
  "Nova Scotia","Ontario","Prince Edward Island","Quebec","Saskatchewan","Northwest Territories",
  "Nunavut","Yukon"
];

const GB_REGIONS = ["England","Scotland","Wales","Northern Ireland"];

const STATES_BY_COUNTRY = {
  "United States": US_STATES,
  "Nigeria": NG_STATES,
  "Canada": CA_PROVINCES,
  "United Kingdom": GB_REGIONS,
};

function populateCountrySelect(selectId, selected) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.innerHTML = '<option value="">Select country</option>' +
    COUNTRIES.map(c => `<option value="${c.name}" data-dial="${c.dial}" ${c.name === selected ? 'selected' : ''}>${c.name}</option>`).join('');
}

function onCountryChange(countrySelectId, dialDisplayId, stateSelectId, selectedState) {
  const countrySel = document.getElementById(countrySelectId);
  const country = countrySel.value;
  const opt = countrySel.options[countrySel.selectedIndex];
  const dial = opt ? opt.dataset.dial || '' : '';

  if (dialDisplayId) {
    const dialEl = document.getElementById(dialDisplayId);
    if (dialEl) {
      if (dialEl.tagName === 'INPUT') dialEl.value = dial;
      else dialEl.textContent = dial || '+--';
    }
  }

  if (stateSelectId) {
    const stateSel = document.getElementById(stateSelectId);
    if (stateSel) {
      const states = STATES_BY_COUNTRY[country];
      if (states) {
        stateSel.innerHTML = '<option value="">Select state/province</option>' +
          states.map(s => `<option value="${s}" ${s === selectedState ? 'selected' : ''}>${s}</option>`).join('');
        stateSel.disabled = false;
      } else {
        stateSel.innerHTML = '<option value="">N/A — enter in address</option>';
        stateSel.disabled = false;
      }
    }
  }
}
